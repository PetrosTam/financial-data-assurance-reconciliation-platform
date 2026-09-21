package com.petros.thesis.jforex;

import com.dukascopy.api.IAccount;
import com.dukascopy.api.IBar;
import com.dukascopy.api.IContext;
import com.dukascopy.api.IHistory;
import com.dukascopy.api.IMessage;
import com.dukascopy.api.IStrategy;
import com.dukascopy.api.ITick;
import com.dukascopy.api.Instrument;
import com.dukascopy.api.JFException;
import com.dukascopy.api.LoadingDataListener;
import com.dukascopy.api.LoadingProgressListener;
import com.dukascopy.api.OfferSide;
import com.dukascopy.api.Period;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.FileAlreadyExistsException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.time.Instant;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeFormatterBuilder;
import java.util.Collections;
import java.util.Locale;
import java.util.Objects;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Streams one historical JForex tick interval to a local CSV artifact.
 *
 * <p>This strategy deliberately separates historical acquisition from live
 * callbacks. Only ticks delivered by {@link IHistory#readTicks} are written
 * to the output artifact.</p>
 *
 * <p>The temporary file is promoted to the final output only after the load
 * has completed successfully and all local validation checks have passed.</p>
 */
public final class HistoricalTickProbe implements IStrategy {

    private static final DateTimeFormatter ISO_UTC_MILLIS =
            new DateTimeFormatterBuilder()
                    .appendInstant(3)
                    .toFormatter();

    private static final String CSV_HEADER =
            "event_time_utc,"
                    + "epoch_ms,"
                    + "bid,"
                    + "ask,"
                    + "bid_volume,"
                    + "ask_volume\n";

    private final Instrument instrument;
    private final long fromEpochMs;
    private final long toEpochMs;
    private final Path output;
    private final Path temporaryOutput;

    private final AtomicLong rows = new AtomicLong();

    private BufferedWriter writer;

    private volatile Long firstEpochMs;
    private volatile Long lastEpochMs;

    private volatile boolean loadFinished;
    private volatile boolean allDataLoaded;
    private volatile Throwable failure;

    public HistoricalTickProbe(
            Instrument instrument,
            Instant from,
            Instant to,
            Path output
    ) {
        this.instrument = Objects.requireNonNull(
                instrument,
                "instrument"
        );

        Objects.requireNonNull(from, "from");
        Objects.requireNonNull(to, "to");

        this.output = Objects.requireNonNull(
                output,
                "output"
        );

        requireMillisecondAligned("from", from);
        requireMillisecondAligned("to", to);

        if (to.isBefore(from)) {
            throw new IllegalArgumentException(
                    "Historical tick range is invalid: "
                            + "to must be greater than or equal to from"
            );
        }

        this.fromEpochMs = from.toEpochMilli();
        this.toEpochMs = to.toEpochMilli();

        Path outputFileName = output.getFileName();

        if (outputFileName == null) {
            throw new IllegalArgumentException(
                    "Output path must reference a file: "
                            + output
            );
        }

        this.temporaryOutput = output.resolveSibling(
                outputFileName.toString() + ".part"
        );
    }

    @Override
    public void onStart(IContext context) throws JFException {

        Objects.requireNonNull(context, "context");

        try {
            /*
             * Main also establishes the subscription before strategy
             * startup. Keeping this check inside the strategy makes the
             * acquisition component self-contained.
             *
             * lock=true means JForex waits for subscription completion.
             */
            context.setSubscribedInstruments(
                    Collections.singleton(instrument),
                    true
            );

            openTemporaryOutput();

            IHistory history = context.getHistory();

            history.readTicks(
                    instrument,
                    fromEpochMs,
                    toEpochMs,

                    new LoadingDataListener() {

                        @Override
                        public void newTick(
                                Instrument tickInstrument,
                                long time,
                                double ask,
                                double bid,
                                double askVol,
                                double bidVol
                        ) {
                            handleHistoricalTick(
                                    tickInstrument,
                                    time,
                                    bid,
                                    ask,
                                    bidVol,
                                    askVol
                            );
                        }

                        @Override
                        public void newBar(
                                Instrument barInstrument,
                                Period period,
                                OfferSide side,
                                long time,
                                double open,
                                double close,
                                double low,
                                double high,
                                double vol
                        ) {
                            /*
                             * readTicks() is expected to deliver ticks.
                             * An unexpected bar callback is treated as an
                             * acquisition-contract violation.
                             */
                            recordFailure(
                                    new IllegalStateException(
                                            "Unexpected bar callback while "
                                                    + "loading historical ticks: "
                                                    + "instrument="
                                                    + barInstrument
                                                    + ", period="
                                                    + period
                                                    + ", side="
                                                    + side
                                    )
                            );
                        }
                    },

                    new LoadingProgressListener() {

                        @Override
                        public void dataLoaded(
                                long start,
                                long end,
                                long currentPosition,
                                String information
                        ) {
                            /*
                             * No per-chunk output.
                             *
                             * The acquisition artifact and final metadata
                             * provide the evidence needed by the research
                             * workflow without noisy provider progress logs.
                             */
                        }

                        @Override
                        public void loadingFinished(
                                boolean complete,
                                long start,
                                long end,
                                long currentPosition
                        ) {
                            allDataLoaded = complete;
                            loadFinished = true;

                            try {
                                closeWriter();

                                System.out.println(
                                        "Historical load finished: "
                                                + "allDataLoaded="
                                                + complete
                                );

                                System.out.println(
                                        "Rows=" + rows.get()
                                );

                                System.out.println(
                                        "First epoch_ms="
                                                + firstEpochMs
                                );

                                System.out.println(
                                        "Last epoch_ms="
                                                + lastEpochMs
                                );

                            } catch (RuntimeException e) {
                                recordFailure(e);

                            } finally {
                                context.stop();
                            }
                        }

                        @Override
                        public boolean stopJob() {
                            /*
                             * A local validation/I/O failure makes the
                             * outstanding provider load no longer useful.
                             */
                            return failure != null
                                    || context.isStopped();
                        }
                    }
            );

        } catch (JFException e) {
            recordFailure(e);
            closeAfterStartFailure(e);
            throw e;

        } catch (RuntimeException e) {
            recordFailure(e);
            closeAfterStartFailure(e);
            throw e;
        }
    }

    private synchronized void handleHistoricalTick(
            Instrument tickInstrument,
            long epochMs,
            double bid,
            double ask,
            double bidVolume,
            double askVolume
    ) {

        /*
         * Once the first failure has occurred we preserve that root cause
         * and do not write additional observations.
         */
        if (failure != null) {
            return;
        }

        if (!instrument.equals(tickInstrument)) {
            recordFailure(
                    new IllegalStateException(
                            "Unexpected instrument in historical "
                                    + "tick callback: "
                                    + tickInstrument
                                    + "; expected "
                                    + instrument
                    )
            );
            return;
        }

        if (writer == null) {
            recordFailure(
                    new IllegalStateException(
                            "Historical tick received while "
                                    + "output writer is not open"
                    )
            );
            return;
        }

        if (!validateTick(
                epochMs,
                bid,
                ask,
                bidVolume,
                askVolume
        )) {
            return;
        }

        /*
         * Equal millisecond timestamps are deliberately allowed.
         *
         * The provider may legitimately deliver more than one observation
         * at the same millisecond. Raw acquisition must preserve those rows
         * rather than silently deduplicate them.
         */
        if (
                lastEpochMs != null
                        && epochMs < lastEpochMs
        ) {
            recordFailure(
                    new IllegalStateException(
                            "Out-of-order historical tick: "
                                    + epochMs
                                    + " arrived after "
                                    + lastEpochMs
                    )
            );
            return;
        }

        try {
            /*
             * Keep explicit LF rather than platform-specific %n.
             *
             * This preserves deterministic byte-level output and therefore
             * stable SHA-256 values across equivalent executions.
             */
            writer.write(
                    String.format(
                            Locale.ROOT,
                            "%s,%d,%.10f,%.10f,%.10f,%.10f\n",
                            ISO_UTC_MILLIS.format(
                                    Instant.ofEpochMilli(epochMs)
                            ),
                            epochMs,
                            bid,
                            ask,
                            bidVolume,
                            askVolume
                    )
            );

        } catch (IOException e) {
            recordFailure(
                    new IllegalStateException(
                            "Failed writing historical tick CSV",
                            e
                    )
            );
            return;
        }

        /*
         * Update observable state only after the complete CSV row has
         * successfully been handed to the writer.
         */
        if (firstEpochMs == null) {
            firstEpochMs = epochMs;
        }

        lastEpochMs = epochMs;
        rows.incrementAndGet();
    }

    private boolean validateTick(
            long epochMs,
            double bid,
            double ask,
            double bidVolume,
            double askVolume
    ) {

        /*
         * JForex readTicks(from, to) includes a tick whose timestamp is
         * exactly equal to 'to'. Enforce that same inclusive contract
         * locally.
         */
        if (
                epochMs < fromEpochMs
                        || epochMs > toEpochMs
        ) {
            recordFailure(
                    new IllegalStateException(
                            "Historical tick outside requested "
                                    + "interval: "
                                    + epochMs
                                    + " not in ["
                                    + fromEpochMs
                                    + ", "
                                    + toEpochMs
                                    + "]"
                    )
            );
            return false;
        }

        if (
                !Double.isFinite(bid)
                        || !Double.isFinite(ask)
        ) {
            recordFailure(
                    new IllegalStateException(
                            "Historical tick contains "
                                    + "non-finite price: "
                                    + "bid="
                                    + bid
                                    + ", ask="
                                    + ask
                    )
            );
            return false;
        }

        if (
                bid <= 0.0
                        || ask <= 0.0
        ) {
            recordFailure(
                    new IllegalStateException(
                            "Historical tick contains "
                                    + "non-positive price: "
                                    + "bid="
                                    + bid
                                    + ", ask="
                                    + ask
                    )
            );
            return false;
        }

        if (ask < bid) {
            recordFailure(
                    new IllegalStateException(
                            "Historical tick has ask < bid: "
                                    + "bid="
                                    + bid
                                    + ", ask="
                                    + ask
                    )
            );
            return false;
        }

        if (
                !Double.isFinite(bidVolume)
                        || !Double.isFinite(askVolume)
        ) {
            recordFailure(
                    new IllegalStateException(
                            "Historical tick contains "
                                    + "non-finite volume: "
                                    + "bidVolume="
                                    + bidVolume
                                    + ", askVolume="
                                    + askVolume
                    )
            );
            return false;
        }

        /*
         * Zero volume is retained as valid provider data.
         * Negative volume is structurally invalid.
         */
        if (
                bidVolume < 0.0
                        || askVolume < 0.0
        ) {
            recordFailure(
                    new IllegalStateException(
                            "Historical tick contains "
                                    + "negative volume: "
                                    + "bidVolume="
                                    + bidVolume
                                    + ", askVolume="
                                    + askVolume
                    )
            );
            return false;
        }

        return true;
    }

    private void openTemporaryOutput() throws JFException {

        try {
            Path parent =
                    output.toAbsolutePath().getParent();

            if (parent != null) {
                Files.createDirectories(parent);
            }

            /*
             * Never delete or replace an existing .part artifact.
             *
             * Every acquisition already has a unique run directory.
             * Finding a pre-existing .part file therefore indicates stale
             * evidence or an unexpected collision and must fail closed.
             */
            writer = Files.newBufferedWriter(
                    temporaryOutput,
                    StandardCharsets.UTF_8,
                    StandardOpenOption.CREATE_NEW,
                    StandardOpenOption.WRITE
            );

            writer.write(CSV_HEADER);

        } catch (IOException e) {
            recordFailure(e);

            throw new JFException(
                    "Could not create temporary output file: "
                            + temporaryOutput,
                    e
            );
        }
    }

    private void closeAfterStartFailure(
            Throwable originalFailure
    ) {

        try {
            closeWriter();

        } catch (RuntimeException closeFailure) {
            originalFailure.addSuppressed(
                    closeFailure
            );

            recordFailure(closeFailure);
        }
    }

    private synchronized void closeWriter() {

        if (writer == null) {
            return;
        }

        BufferedWriter writerToClose = writer;

        /*
         * Clear the shared reference first so that no subsequent callback
         * can attempt another write through this object.
         */
        writer = null;

        try {
            /*
             * BufferedWriter.close() flushes buffered characters before
             * closing the underlying stream.
             */
            writerToClose.close();

        } catch (IOException e) {
            IllegalStateException wrapped =
                    new IllegalStateException(
                            "Failed closing historical tick CSV",
                            e
                    );

            recordFailure(wrapped);
            throw wrapped;
        }
    }

    public synchronized void assertSuccessful() {

        if (failure != null) {
            throw new IllegalStateException(
                    "Historical probe failed",
                    failure
            );
        }

        if (!loadFinished) {
            throw new IllegalStateException(
                    "Historical load did not report completion"
            );
        }

        if (!allDataLoaded) {
            throw new IllegalStateException(
                    "Historical load completed with "
                            + "allDataLoaded=false"
            );
        }

        long rowCount = rows.get();

        /*
         * Current acquisition policy remains fail-closed for zero-row
         * windows.
         *
         * A future explicit market-closure/allow-empty policy must be
         * introduced separately rather than silently treating an empty
         * response as successful provider evidence.
         */
        if (rowCount <= 0) {
            throw new IllegalStateException(
                    "Historical load returned zero rows"
            );
        }

        if (
                firstEpochMs == null
                        || lastEpochMs == null
        ) {
            throw new IllegalStateException(
                    "Historical load returned rows but "
                            + "timestamp boundaries are missing"
            );
        }

        if (
                firstEpochMs < fromEpochMs
                        || firstEpochMs > toEpochMs
        ) {
            throw new IllegalStateException(
                    "First historical tick lies outside "
                            + "requested interval: "
                            + firstEpochMs
            );
        }

        if (
                lastEpochMs < fromEpochMs
                        || lastEpochMs > toEpochMs
        ) {
            throw new IllegalStateException(
                    "Last historical tick lies outside "
                            + "requested interval: "
                            + lastEpochMs
            );
        }

        if (lastEpochMs < firstEpochMs) {
            throw new IllegalStateException(
                    "Historical tick boundaries are inconsistent: "
                            + "last_epoch_ms < first_epoch_ms"
            );
        }

        if (writer != null) {
            throw new IllegalStateException(
                    "Historical output writer is still open"
            );
        }

        if (!Files.isRegularFile(temporaryOutput)) {
            throw new IllegalStateException(
                    "Expected temporary output does not exist: "
                            + temporaryOutput
            );
        }

        if (Files.exists(output)) {
            throw new IllegalStateException(
                    "Final output already exists before commit: "
                            + output
            );
        }
    }

    public void commitOutput() throws IOException {

        assertSuccessful();

        /*
         * Never silently overwrite a previous research artifact.
         */
        if (Files.exists(output)) {
            throw new FileAlreadyExistsException(
                    output.toString()
            );
        }

        try {
            Files.move(
                    temporaryOutput,
                    output,
                    StandardCopyOption.ATOMIC_MOVE
            );

        } catch (AtomicMoveNotSupportedException e) {
            /*
             * Fall back to a normal same-filesystem move while retaining
             * no-overwrite semantics.
             */
            Files.move(
                    temporaryOutput,
                    output
            );
        }

        /*
         * Verify the promotion postcondition instead of assuming the
         * filesystem operation produced the expected state.
         */
        if (!Files.isRegularFile(output)) {
            throw new IOException(
                    "Committed historical output does not exist: "
                            + output
            );
        }

        if (Files.exists(temporaryOutput)) {
            throw new IOException(
                    "Temporary historical output still exists "
                            + "after commit: "
                            + temporaryOutput
            );
        }
    }

    private synchronized void recordFailure(
            Throwable throwable
    ) {
        Objects.requireNonNull(
                throwable,
                "throwable"
        );

        /*
         * Preserve the first/root failure.
         *
         * Cleanup failures must not overwrite the original reason that
         * caused acquisition to become invalid.
         */
        if (failure == null) {
            failure = throwable;
        }
    }

    private static void requireMillisecondAligned(
            String name,
            Instant instant
    ) {

        Instant millisecondAligned =
                Instant.ofEpochMilli(
                        instant.toEpochMilli()
                );

        if (!millisecondAligned.equals(instant)) {
            throw new IllegalArgumentException(
                    name
                            + " must use millisecond precision "
                            + "or coarser: "
                            + instant
            );
        }
    }

    public long getRows() {
        return rows.get();
    }

    public Long getFirstEpochMs() {
        return firstEpochMs;
    }

    public Long getLastEpochMs() {
        return lastEpochMs;
    }

    public boolean isAllDataLoaded() {
        return allDataLoaded;
    }

    @Override
    public void onTick(
            Instrument instrument,
            ITick tick
    ) {
        /*
         * Intentionally ignored.
         *
         * This artifact contains only historical observations returned by
         * IHistory.readTicks(). Live ticks must never be mixed into it.
         */
    }

    @Override
    public void onBar(
            Instrument instrument,
            Period period,
            IBar askBar,
            IBar bidBar
    ) {
        // Live bar callbacks are outside this acquisition contract.
    }

    @Override
    public void onMessage(
            IMessage message
    ) {
        /*
         * Trading/order messages are outside this acquisition contract.
         * This platform does not perform trade execution.
         */
    }

    @Override
    public void onAccount(
            IAccount account
    ) {
        // Account state is outside this acquisition contract.
    }

    @Override
    public void onStop() {

        /*
         * Safety-net close for provider failure, timeout, manual stop or
         * strategy shutdown.
         *
         * Do not throw from onStop; retain cleanup failure as probe state
         * so Main/assertSuccessful can report the acquisition as invalid.
         */
        try {
            closeWriter();

        } catch (RuntimeException e) {
            recordFailure(e);
        }
    }
}