package com.petros.thesis.jforex;

import com.dukascopy.api.Instrument;
import com.dukascopy.api.system.ClientFactory;
import com.dukascopy.api.system.IClient;
import com.dukascopy.api.system.ISystemListener;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.FileAlreadyExistsException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeFormatterBuilder;
import java.util.Collections;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

public final class Main {

    /*
     * Official Dukascopy DEMO endpoint used by the JForex SDK examples.
     *
     * Do not place credentials in source code. They are read exclusively
     * from environment variables below.
     */
    private static final String DEMO_JNLP =
            "http://platform.dukascopy.com/demo_3/jforex_3.jnlp";

    private static final String ACQUISITION_ROUTE =
            "JForex IHistory.readTicks via DEMO endpoint";

    private static final String PROVIDER_PATH_CODE =
            "dukascopy";

    /*
     * Runtime safety boundaries.
     *
     * Probe timeout remains configurable from the CLI because historical
     * loading time depends on provider/network behaviour. Connection and
     * subscription timeouts remain fixed operational safeguards.
     */
    private static final long CONNECT_TIMEOUT_MS =
            30_000L;

    private static final long SUBSCRIPTION_TIMEOUT_MS =
            30_000L;

    private static final long DEFAULT_PROBE_TIMEOUT_MS =
            120_000L;

    private static final long DISCONNECT_TIMEOUT_MS =
            10_000L;

    /*
     * The compatibility pilot deliberately acquires exactly one canonical
     * UTC hour per run.
     *
     * This is a fail-closed response to observed Dukascopy/JForex behaviour
     * where a multi-hour request returned a partial result while reporting
     * allDataLoaded=true.
     *
     * One acquisition run therefore covers:
     *
     * HH:00:00.000 through HH:59:59.999 inclusive.
     */
    private static final long CANONICAL_HOUR_MILLIS =
            TimeUnit.HOURS.toMillis(1L);

    private static final String WINDOW_POLICY =
            "canonical_utc_hour";

    private static final DateTimeFormatter MARKET_DATE_PATH =
            DateTimeFormatter.ofPattern("yyyy-MM-dd")
                    .withZone(ZoneOffset.UTC);

    private static final DateTimeFormatter WINDOW_TIME_PATH =
            DateTimeFormatter.ofPattern("HHmm")
                    .withZone(ZoneOffset.UTC);

    private static final DateTimeFormatter ACQUISITION_TIME_PATH =
            new DateTimeFormatterBuilder()
                    .appendPattern("yyyy-MM-dd'T'HHmmss.SSS'Z'")
                    .toFormatter()
                    .withZone(ZoneOffset.UTC);

    private static final DateTimeFormatter ISO_UTC_MILLIS =
            new DateTimeFormatterBuilder()
                    .appendInstant(3)
                    .toFormatter();

    private Main() {
    }

    public static void main(String[] args) {
        int exitCode = 0;

        try {
            run(args);
        } catch (Throwable t) {
            exitCode = 1;

            System.err.println(
                    "Probe failed: " + safeMessage(t)
            );

            t.printStackTrace(System.err);
        }

        /*
         * Maven exec:exec launches this application in a dedicated child JVM.
         *
         * The Dukascopy SDK may leave transport/background threads alive after
         * the logical work has finished, therefore the child JVM is terminated
         * explicitly with the acquisition result code.
         */
        System.exit(exitCode);
    }

    private static void run(String[] args) throws Exception {

        /*
         * Parse and validate the acquisition contract BEFORE reading
         * credentials or contacting Dukascopy.
         *
         * Invalid windows therefore fail closed without authentication,
         * provider access, or creation of a data artefact.
         */
        RunConfiguration config =
                RunConfiguration.parse(args);

        String username =
                requireEnv("DUKASCOPY_DEMO_USERNAME");

        String password =
                requireEnv("DUKASCOPY_DEMO_PASSWORD");

        String runId =
                UUID.randomUUID().toString();

        Instant startedAt =
                Instant.now();

        Path runDirectory =
                createRunDirectory(
                        config,
                        startedAt
                );

        Path output =
                runDirectory.resolve("ticks.csv");

        Path metadata =
                runDirectory.resolve("metadata.json");

        CountDownLatch disconnected =
                new CountDownLatch(1);

        IClient client =
                ClientFactory.getDefaultInstance();

        client.setSystemListener(
                new ISystemListener() {
                    @Override
                    public void onStart(long processId) {
                        System.out.println(
                                "Strategy started: "
                                        + processId
                        );
                    }

                    @Override
                    public void onStop(long processId) {
                        System.out.println(
                                "Strategy stopped: "
                                        + processId
                        );
                    }

                    @Override
                    public void onConnect() {
                        System.out.println(
                                "Connected to Dukascopy DEMO."
                        );
                    }

                    @Override
                    public void onDisconnect() {
                        System.out.println(
                                "Disconnected from Dukascopy DEMO."
                        );

                        disconnected.countDown();
                    }
                }
        );

        HistoricalTickProbe probe =
                new HistoricalTickProbe(
                        config.instrument,
                        config.requestedFrom,
                        config.requestedTo,
                        output
                );

        try {
            printConfiguration(config);

            client.connect(
                    DEMO_JNLP,
                    username,
                    password
            );

            waitForConnection(client);

            Set<Instrument> instruments =
                    Collections.singleton(
                            config.instrument
                    );

            /*
             * Dukascopy documents standalone instrument subscription as
             * asynchronous. Do not race strategy startup against subscription.
             */
            client.setSubscribedInstruments(
                    instruments
            );

            waitForSubscription(
                    client,
                    config.instrument
            );

            long processId =
                    client.startStrategy(probe);

            waitForStrategyCompletion(
                    client,
                    processId,
                    config.probeTimeoutMs
            );

            /*
             * The probe performs data-level success checks before the temporary
             * output is promoted to the canonical ticks.csv.
             */
            probe.assertSuccessful();

            probe.commitOutput();

            Instant completedAt =
                    Instant.now();

            String sha256 =
                    sha256(output);

            writeMetadata(
                    metadata,
                    runDirectory,
                    output,
                    runId,
                    startedAt,
                    completedAt,
                    config,
                    probe,
                    sha256
            );

            System.out.println(
                    "Probe finished successfully."
            );

            System.out.println(
                    "Run directory: "
                            + runDirectory
                                    .toAbsolutePath()
                                    .normalize()
            );

            System.out.println(
                    "Output: "
                            + output
                                    .toAbsolutePath()
                                    .normalize()
            );

            System.out.println(
                    "Metadata: "
                            + metadata
                                    .toAbsolutePath()
                                    .normalize()
            );

            System.out.println(
                    "SHA-256: " + sha256
            );

        } finally {
            disconnect(
                    client,
                    disconnected
            );
        }
    }

    private static void printConfiguration(
            RunConfiguration config
    ) {
        System.out.println(
                "Instrument: "
                        + config.instrument
        );

        System.out.println(
                "Requested from UTC: "
                        + ISO_UTC_MILLIS.format(
                                config.requestedFrom
                        )
        );

        System.out.println(
                "Requested to UTC: "
                        + ISO_UTC_MILLIS.format(
                                config.requestedTo
                        )
        );

        System.out.println(
                "Window policy: "
                        + WINDOW_POLICY
        );

        System.out.println(
                "Probe timeout ms: "
                        + config.probeTimeoutMs
        );
    }

    private static Path createRunDirectory(
            RunConfiguration config,
            Instant startedAt
    ) throws IOException {

        Path windowRoot =
                config.outputRoot
                        .resolve(
                                PROVIDER_PATH_CODE
                        )
                        .resolve(
                                instrumentPathCode(
                                        config.instrument
                                )
                        )
                        .resolve(
                                MARKET_DATE_PATH.format(
                                        config.requestedFrom
                                )
                        )
                        .resolve(
                                buildWindowDirectoryName(
                                        config
                                )
                        );

        Files.createDirectories(windowRoot);

        String acquisitionTime =
                ACQUISITION_TIME_PATH.format(
                        startedAt
                );

        for (
                int attempt = 1;
                attempt <= 99;
                attempt++
        ) {
            String directoryName;

            if (attempt == 1) {
                directoryName =
                        acquisitionTime;
            } else {
                directoryName =
                        acquisitionTime
                                + "-"
                                + String.format(
                                        Locale.ROOT,
                                        "%02d",
                                        attempt
                                );
            }

            Path candidate =
                    windowRoot.resolve(
                            directoryName
                    );

            try {
                return Files.createDirectory(
                        candidate
                );
            } catch (
                    FileAlreadyExistsException ignored
            ) {
                /*
                 * Extremely unlikely millisecond-level collision.
                 *
                 * Retry deterministically without overwriting prior
                 * acquisition evidence.
                 */
            }
        }

        throw new IOException(
                "Could not allocate a unique run directory under "
                        + windowRoot
        );
    }

    private static String buildWindowDirectoryName(
            RunConfiguration config
    ) {
        Instant exclusiveEnd =
                config.requestedTo
                        .plusMillis(1L);

        String start =
                WINDOW_TIME_PATH.format(
                        config.requestedFrom
                );

        ZonedDateTime fromUtc =
                config.requestedFrom
                        .atZone(
                                ZoneOffset.UTC
                        );

        ZonedDateTime exclusiveEndUtc =
                exclusiveEnd
                        .atZone(
                                ZoneOffset.UTC
                        );

        boolean endsAtNextMidnight =
                exclusiveEndUtc
                        .toLocalDate()
                        .equals(
                                fromUtc
                                        .toLocalDate()
                                        .plusDays(1L)
                        )
                        && exclusiveEndUtc
                                .getHour() == 0
                        && exclusiveEndUtc
                                .getMinute() == 0
                        && exclusiveEndUtc
                                .getSecond() == 0
                        && exclusiveEndUtc
                                .getNano() == 0;

        String end =
                endsAtNextMidnight
                        ? "2400"
                        : WINDOW_TIME_PATH.format(
                                exclusiveEnd
                        );

        return start
                + "-"
                + end
                + "utc";
    }

    private static String instrumentPathCode(
            Instrument instrument
    ) {
        String raw =
                instrument
                        .toString()
                        .toLowerCase(
                                Locale.ROOT
                        );

        StringBuilder result =
                new StringBuilder();

        for (
                int i = 0;
                i < raw.length();
                i++
        ) {
            char c =
                    raw.charAt(i);

            if (
                    Character
                            .isLetterOrDigit(c)
            ) {
                result.append(c);
            }
        }

        if (result.length() == 0) {
            throw new IllegalArgumentException(
                    "Could not derive path code for instrument "
                            + instrument
            );
        }

        return result.toString();
    }

    private static void waitForConnection(
            IClient client
    ) throws InterruptedException {

        long deadline =
                System.currentTimeMillis()
                        + CONNECT_TIMEOUT_MS;

        while (
                !client.isConnected()
                        && System.currentTimeMillis()
                        < deadline
        ) {
            Thread.sleep(250L);
        }

        if (!client.isConnected()) {
            throw new IllegalStateException(
                    "Dukascopy connection timeout after "
                            + CONNECT_TIMEOUT_MS
                            + " ms"
            );
        }
    }

    private static void waitForSubscription(
            IClient client,
            Instrument instrument
    ) throws InterruptedException {

        long deadline =
                System.currentTimeMillis()
                        + SUBSCRIPTION_TIMEOUT_MS;

        while (
                client.isConnected()
                        && !client
                                .getSubscribedInstruments()
                                .contains(instrument)
                        && System.currentTimeMillis()
                                < deadline
        ) {
            Thread.sleep(100L);
        }

        if (!client.isConnected()) {
            throw new IllegalStateException(
                    "Dukascopy disconnected while waiting "
                            + "for instrument subscription: "
                            + instrument
            );
        }

        if (
                !client
                        .getSubscribedInstruments()
                        .contains(instrument)
        ) {
            throw new IllegalStateException(
                    "Instrument subscription timeout after "
                            + SUBSCRIPTION_TIMEOUT_MS
                            + " ms for "
                            + instrument
            );
        }

        System.out.println(
                "Instrument subscription confirmed: "
                        + instrument
        );
    }

    private static void waitForStrategyCompletion(
            IClient client,
            long processId,
            long probeTimeoutMs
    ) throws InterruptedException {

        long deadline =
                System.currentTimeMillis()
                        + probeTimeoutMs;

        while (
                client
                        .getStartedStrategies()
                        .containsKey(processId)
                        && System.currentTimeMillis()
                                < deadline
        ) {
            Thread.sleep(250L);
        }

        if (
                client
                        .getStartedStrategies()
                        .containsKey(processId)
        ) {
            /*
             * disconnect() in the caller's finally block stops running
             * strategies as part of JForex SDK shutdown.
             */
            throw new IllegalStateException(
                    "Historical probe timeout after "
                            + probeTimeoutMs
                            + " ms"
            );
        }
    }

    private static void disconnect(
            IClient client,
            CountDownLatch disconnected
    ) throws InterruptedException {

        if (!client.isConnected()) {
            return;
        }

        client.disconnect();

        if (
                !disconnected.await(
                        DISCONNECT_TIMEOUT_MS,
                        TimeUnit.MILLISECONDS
                )
        ) {
            /*
             * This callback timeout has already been observed empirically
             * without invalidating successful historical acquisitions.
             *
             * Keep it observable but do not rewrite a completed acquisition
             * as failed solely because the SDK omitted the disconnect callback.
             */
            System.err.println(
                    "Warning: Dukascopy disconnect callback "
                            + "was not observed within "
                            + DISCONNECT_TIMEOUT_MS
                            + " ms"
            );
        }
    }

    private static void writeMetadata(
            Path metadata,
            Path runDirectory,
            Path output,
            String runId,
            Instant startedAt,
            Instant completedAt,
            RunConfiguration config,
            HistoricalTickProbe probe,
            String sha256
    ) throws IOException {

        Files.createDirectories(
                runDirectory
        );

        String sdkVersion =
                System.getProperty(
                        "dukascopy.sdk.version",
                        "UNKNOWN"
                );

        /*
         * Metadata schema version 2 adds an explicit acquisition-window
         * policy. Historical schema-v1 artefacts remain immutable.
         */
        String json =
                "{\n"
                        + "  \"schema_version\": \"2\",\n"
                        + "  \"run_id\": "
                        + jsonString(runId)
                        + ",\n"
                        + "  \"provider\": \"Dukascopy\",\n"
                        + "  \"acquisition_route\": "
                        + jsonString(
                                ACQUISITION_ROUTE
                        )
                        + ",\n"
                        + "  \"endpoint\": "
                        + jsonString(
                                DEMO_JNLP
                        )
                        + ",\n"
                        + "  \"dukascopy_sdk_version\": "
                        + jsonString(
                                sdkVersion
                        )
                        + ",\n"
                        + "  \"instrument\": "
                        + jsonString(
                                config.instrument
                                        .toString()
                        )
                        + ",\n"
                        + "  \"window_policy\": "
                        + jsonString(
                                WINDOW_POLICY
                        )
                        + ",\n"
                        + "  \"requested_from_utc\": "
                        + jsonString(
                                ISO_UTC_MILLIS.format(
                                        config.requestedFrom
                                )
                        )
                        + ",\n"
                        + "  \"requested_to_utc\": "
                        + jsonString(
                                ISO_UTC_MILLIS.format(
                                        config.requestedTo
                                )
                        )
                        + ",\n"
                        + "  \"requested_duration_ms\": "
                        + CANONICAL_HOUR_MILLIS
                        + ",\n"
                        + "  \"probe_timeout_ms\": "
                        + config.probeTimeoutMs
                        + ",\n"
                        + "  \"all_data_loaded\": "
                        + probe.isAllDataLoaded()
                        + ",\n"
                        + "  \"rows\": "
                        + probe.getRows()
                        + ",\n"
                        + "  \"first_epoch_ms\": "
                        + probe.getFirstEpochMs()
                        + ",\n"
                        + "  \"last_epoch_ms\": "
                        + probe.getLastEpochMs()
                        + ",\n"
                        + "  \"run_directory\": "
                        + jsonString(
                                runDirectory
                                        .toAbsolutePath()
                                        .normalize()
                                        .toString()
                        )
                        + ",\n"
                        + "  \"output_csv\": "
                        + jsonString(
                                output
                                        .getFileName()
                                        .toString()
                        )
                        + ",\n"
                        + "  \"output_sha256\": "
                        + jsonString(
                                sha256
                        )
                        + ",\n"
                        + "  \"started_at_utc\": "
                        + jsonString(
                                startedAt.toString()
                        )
                        + ",\n"
                        + "  \"completed_at_utc\": "
                        + jsonString(
                                completedAt.toString()
                        )
                        + ",\n"
                        + "  \"java_version\": "
                        + jsonString(
                                System.getProperty(
                                        "java.version"
                                )
                        )
                        + ",\n"
                        + "  \"os_name\": "
                        + jsonString(
                                System.getProperty(
                                        "os.name"
                                )
                        )
                        + "\n"
                        + "}\n";

        Files.write(
                metadata,
                json.getBytes(
                        StandardCharsets.UTF_8
                )
        );
    }

    private static String sha256(
            Path path
    ) throws IOException,
            NoSuchAlgorithmException {

        MessageDigest digest =
                MessageDigest.getInstance(
                        "SHA-256"
                );

        byte[] buffer =
                new byte[8192];

        try (
                InputStream in =
                        Files.newInputStream(path)
        ) {
            int read;

            while (
                    (read = in.read(buffer))
                            >= 0
            ) {
                if (read > 0) {
                    digest.update(
                            buffer,
                            0,
                            read
                    );
                }
            }
        }

        StringBuilder hex =
                new StringBuilder();

        for (byte b : digest.digest()) {
            hex.append(
                    String.format(
                            Locale.ROOT,
                            "%02x",
                            b & 0xff
                    )
            );
        }

        return hex.toString();
    }

    private static String jsonString(
            String value
    ) {
        if (value == null) {
            return "null";
        }

        String escaped =
                value
                        .replace(
                                "\\",
                                "\\\\"
                        )
                        .replace(
                                "\"",
                                "\\\""
                        )
                        .replace(
                                "\r",
                                "\\r"
                        )
                        .replace(
                                "\n",
                                "\\n"
                        )
                        .replace(
                                "\t",
                                "\\t"
                        );

        return "\""
                + escaped
                + "\"";
    }

    private static String requireEnv(
            String key
    ) {
        String value =
                System.getenv(key);

        if (
                value == null
                        || value
                                .trim()
                                .isEmpty()
        ) {
            throw new IllegalStateException(
                    "Missing environment variable "
                            + key
                            + ". Do not hard-code credentials "
                            + "in source control."
            );
        }

        return value;
    }

    private static String safeMessage(
            Throwable throwable
    ) {
        String message =
                throwable.getMessage();

        if (
                message == null
                        || message
                                .trim()
                                .isEmpty()
        ) {
            return throwable
                    .getClass()
                    .getName();
        }

        return message;
    }

    private static final class RunConfiguration {

        private final Instrument instrument;

        private final Instant requestedFrom;

        private final Instant requestedTo;

        private final Path outputRoot;

        private final long probeTimeoutMs;

        private RunConfiguration(
                Instrument instrument,
                Instant requestedFrom,
                Instant requestedTo,
                Path outputRoot,
                long probeTimeoutMs
        ) {
            this.instrument =
                    instrument;

            this.requestedFrom =
                    requestedFrom;

            this.requestedTo =
                    requestedTo;

            this.outputRoot =
                    outputRoot;

            this.probeTimeoutMs =
                    probeTimeoutMs;
        }

        private static RunConfiguration parse(
                String[] args
        ) {
            Map<String, String> options =
                    parseOptions(args);

            String instrumentText =
                    requireOption(
                            options,
                            "instrument"
                    );

            String fromText =
                    requireOption(
                            options,
                            "from"
                    );

            String toText =
                    requireOption(
                            options,
                            "to"
                    );

            Instrument instrument;

            try {
                instrument =
                        Instrument.fromString(
                                instrumentText
                        );
            } catch (RuntimeException e) {
                throw new IllegalArgumentException(
                        "Unsupported Dukascopy instrument: "
                                + instrumentText,
                        e
                );
            }

            if (instrument == null) {
                throw new IllegalArgumentException(
                        "Unsupported Dukascopy instrument: "
                                + instrumentText
                );
            }

            Instant from =
                    parseInstant(
                            "--from",
                            fromText
                    );

            Instant to =
                    parseInstant(
                            "--to",
                            toText
                    );

            requireMillisecondPrecision(
                    "--from",
                    from
            );

            requireMillisecondPrecision(
                    "--to",
                    to
            );

            if (to.isBefore(from)) {
                throw new IllegalArgumentException(
                        "--to must be greater than "
                                + "or equal to --from"
                );
            }

            requireCanonicalUtcHour(
                    from,
                    to
            );

            Path outputRoot =
                    Paths.get(
                            options.containsKey(
                                    "output-root"
                            )
                                    ? options.get(
                                            "output-root"
                                    )
                                    : "out/runs"
                    )
                            .toAbsolutePath()
                            .normalize();

            long probeTimeoutMs =
                    DEFAULT_PROBE_TIMEOUT_MS;

            if (
                    options.containsKey(
                            "probe-timeout-ms"
                    )
            ) {
                String timeoutText =
                        options.get(
                                "probe-timeout-ms"
                        );

                try {
                    probeTimeoutMs =
                            Long.parseLong(
                                    timeoutText
                            );
                } catch (
                        NumberFormatException e
                ) {
                    throw new IllegalArgumentException(
                            "Invalid --probe-timeout-ms value: "
                                    + timeoutText,
                            e
                    );
                }

                if (probeTimeoutMs <= 0L) {
                    throw new IllegalArgumentException(
                            "--probe-timeout-ms "
                                    + "must be positive"
                    );
                }
            }

            return new RunConfiguration(
                    instrument,
                    from,
                    to,
                    outputRoot,
                    probeTimeoutMs
            );
        }

        private static Instant parseInstant(
                String option,
                String value
        ) {
            try {
                return Instant.parse(value);
            } catch (RuntimeException e) {
                throw new IllegalArgumentException(
                        "Invalid "
                                + option
                                + " UTC instant: "
                                + value,
                        e
                );
            }
        }

        private static void requireCanonicalUtcHour(
                Instant from,
                Instant to
        ) {
            ZonedDateTime fromUtc =
                    from.atZone(
                            ZoneOffset.UTC
                    );

            boolean startsExactlyOnHour =
                    fromUtc.getMinute() == 0
                            && fromUtc
                                    .getSecond() == 0
                            && fromUtc
                                    .getNano() == 0;

            Instant expectedTo =
                    from.plusMillis(
                            CANONICAL_HOUR_MILLIS
                                    - 1L
                    );

            if (
                    !startsExactlyOnHour
                            || !to.equals(
                                    expectedTo
                            )
            ) {
                throw new IllegalArgumentException(
                        "Each acquisition run must cover exactly "
                                + "one canonical UTC hour: "
                                + "HH:00:00.000 through "
                                + "HH:59:59.999 inclusive. "
                                + "Requested: "
                                + ISO_UTC_MILLIS.format(from)
                                + " through "
                                + ISO_UTC_MILLIS.format(to)
                );
            }
        }

        private static Map<String, String> parseOptions(
                String[] args
        ) {
            Map<String, String> options =
                    new HashMap<String, String>();

            for (String arg : args) {

                if (
                        arg == null
                                || !arg.startsWith("--")
                ) {
                    throw new IllegalArgumentException(
                            "Arguments must use "
                                    + "--name=value format. "
                                    + usage()
                    );
                }

                int equals =
                        arg.indexOf('=');

                if (
                        equals <= 2
                                || equals
                                == arg.length() - 1
                ) {
                    throw new IllegalArgumentException(
                            "Invalid argument: "
                                    + arg
                                    + ". "
                                    + usage()
                    );
                }

                String key =
                        arg.substring(
                                2,
                                equals
                        );

                String value =
                        arg.substring(
                                equals + 1
                        );

                if (
                        !key.equals(
                                "instrument"
                        )
                                && !key.equals(
                                        "from"
                                )
                                && !key.equals(
                                        "to"
                                )
                                && !key.equals(
                                        "output-root"
                                )
                                && !key.equals(
                                        "probe-timeout-ms"
                                )
                ) {
                    throw new IllegalArgumentException(
                            "Unknown option --"
                                    + key
                    );
                }

                if (
                        options.put(
                                key,
                                value
                        )
                                != null
                ) {
                    throw new IllegalArgumentException(
                            "Duplicate option --"
                                    + key
                    );
                }
            }

            return options;
        }

        private static String requireOption(
                Map<String, String> options,
                String key
        ) {
            String value =
                    options.get(key);

            if (
                    value == null
                            || value
                                    .trim()
                                    .isEmpty()
            ) {
                throw new IllegalArgumentException(
                        "Missing required option --"
                                + key
                                + ". "
                                + usage()
                );
            }

            return value;
        }

        private static void requireMillisecondPrecision(
                String option,
                Instant instant
        ) {
            Instant millisecondAligned =
                    Instant.ofEpochMilli(
                            instant.toEpochMilli()
                    );

            if (
                    !millisecondAligned.equals(
                            instant
                    )
            ) {
                throw new IllegalArgumentException(
                        option
                                + " must use millisecond "
                                + "precision or coarser: "
                                + instant
                );
            }
        }

        private static String usage() {
            return "Required: "
                    + "--instrument=EUR/USD "
                    + "--from=2026-01-27T12:00:00.000Z "
                    + "--to=2026-01-27T12:59:59.999Z "
                    + "[--output-root=out/runs] "
                    + "[--probe-timeout-ms=120000]";
        }
    }
}