import argparse
import csv
import json
import time
from datetime import datetime
from pathlib import Path

from confluent_kafka import Producer


# Dataset location
DEFAULT_CSV = Path("data/raw/claims.csv")

# Kafka configuration
BOOTSTRAP_SERVERS = "localhost:9092"
TOPIC = "claims.raw"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Replay insurance claims from CSV into Kafka."
    )
    parser.add_argument(
        "--csv",
        default=str(DEFAULT_CSV),
        help="Path to claims.csv",
    )
    parser.add_argument(
        "--seconds-per-day",
        type=float,
        default=1.0,
        help="Simulated seconds per day between claim dates.",
    )
    parser.add_argument(
        "--burst",
        action="store_true",
        help="Publish all claims as quickly as possible.",
    )
    parser.add_argument(
        "--max-claims",
        type=int,
        default=0,
        help="Maximum claims to publish; 0 means all claims.",
    )
    return parser.parse_args()


def parse_date(value):
    """Parse a date without assuming every CSV uses the same format."""
    value = (value or "").strip()

    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%d/%m/%Y",
    ):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass

    return None


def delivery_report(error, message):
    if error:
        print(f"Delivery failed: {error}")
    else:
        print(
            f"Delivered to {message.topic()} "
            f"| partition={message.partition()} "
            f"| offset={message.offset()}"
        )


def main():
    args = parse_args()
    csv_path = Path(args.csv)

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {csv_path.resolve()}"
        )

    if args.seconds_per_day < 0:
        raise ValueError("--seconds-per-day cannot be negative.")

    producer = Producer({
        "bootstrap.servers": BOOTSTRAP_SERVERS,
        "enable.idempotence": True,
    })

    # Read all records and sort by event date.
    with csv_path.open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError("The CSV has no header row.")

        # Find the date column without assuming its capitalization.
        date_column = next(
            (
                name for name in reader.fieldnames
                if name.strip().lower() == "date_of_claim"
            ),
            None,
        )

        if date_column is None:
            raise ValueError(
                "Could not find a 'date_of_claim' column. "
                f"Available columns: {reader.fieldnames}"
            )

        rows = []
        for row in reader:
            parsed = parse_date(row.get(date_column))
            if parsed is None:
                print(
                    "Skipping row with an unrecognized claim date:",
                    row.get(date_column),
                )
                continue

            rows.append((parsed, row))

    rows.sort(key=lambda item: item[0])

    if args.max_claims > 0:
        rows = rows[:args.max_claims]

    if not rows:
        raise ValueError("No valid claims were found in the CSV.")

    print(f"Dataset: {csv_path.resolve()}")
    print(f"Kafka topic: {TOPIC}")
    print(f"Valid claims loaded: {len(rows)}")
    print(f"First claim date: {rows[0][0]}")
    print(f"Last claim date:  {rows[-1][0]}")
    print("Starting replay. Press Ctrl+C to stop.")

    published = 0
    previous_date = None

    try:
        for claim_date, row in rows:
            # Keep the original CSV fields in the Kafka message.
            # Normalize blank cells to empty strings.
            claim = {
                key: (value if value is not None else "")
                for key, value in row.items()
            }

            # Use the hospital ID as the partitioning key.
            hospital_id = (
                claim.get("hospital_id")
                or claim.get("Hospital_ID")
                or claim.get("HOSPITAL_ID")
                or "UNKNOWN_HOSPITAL"
            )

            # In normal mode, wait according to the gap between
            # consecutive claim dates. In burst mode, do not wait.
            if (
                not args.burst
                and previous_date is not None
            ):
                days = (claim_date - previous_date).total_seconds() / 86400
                delay = days * args.seconds_per_day
                if delay > 0:
                    time.sleep(delay)

            producer.produce(
                topic=TOPIC,
                key=str(hospital_id),
                value=json.dumps(claim, ensure_ascii=False),
                callback=delivery_report,
            )

            # Serve delivery callbacks and apply backpressure if needed.
            producer.poll(0)
            published += 1
            previous_date = claim_date

            if published % 100 == 0:
                print(f"Queued {published}/{len(rows)} claims")

        remaining = producer.flush(30)
        if remaining:
            print(f"Warning: {remaining} message(s) remain undelivered.")

        print(f"Replay finished. Claims submitted: {published}")

    except KeyboardInterrupt:
        print("\nReplay interrupted. Waiting for queued messages...")
        producer.flush(30)
        print(f"Claims submitted before interruption: {published}")


if __name__ == "__main__":
    main()
