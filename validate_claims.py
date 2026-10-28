import json
from datetime import date

from confluent_kafka import Consumer, Producer, KafkaException


BOOTSTRAP_SERVERS = "localhost:9092"
INPUT_TOPIC = "claims.raw"
VALID_TOPIC = "claims.valid"
DLQ_TOPIC = "claims.dlq"


consumer = Consumer({
    "bootstrap.servers": BOOTSTRAP_SERVERS,
    "group.id": "claim-validation-v1",
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,
})

producer = Producer({
    "bootstrap.servers": BOOTSTRAP_SERVERS,
    "enable.idempotence": True,
})

valid_count = 0
invalid_count = 0


def validate_claim(claim):
    """Return a list of validation errors."""
    errors = []

    if not isinstance(claim, dict):
        return ["Message must be a JSON object"]

    required_fields = [
        "claim_id",
        "patient_id",
        "hospital_id",
        "date_of_claim",
        "claim_amount_requested_inr",
    ]

    for field in required_fields:
        value = claim.get(field)
        if value is None or str(value).strip() == "":
            errors.append(f"Missing required field: {field}")

    claim_date = str(claim.get("date_of_claim", "")).strip()
    if claim_date:
        try:
            date.fromisoformat(claim_date)
        except ValueError:
            errors.append("date_of_claim must use YYYY-MM-DD format")

    amount = claim.get("claim_amount_requested_inr")
    if amount is not None and str(amount).strip() != "":
        try:
            if float(amount) < 0:
                errors.append("Requested claim amount cannot be negative")
        except (ValueError, TypeError):
            errors.append("Requested claim amount must be numeric")

    return errors


def deliver_and_wait(topic, key, value):
    """Wait for a broker delivery result before committing the input."""
    result = {"done": False, "error": None}

    def callback(error, message):
        result["done"] = True
        result["error"] = error

    producer.produce(
        topic=topic,
        key=key,
        value=json.dumps(value, ensure_ascii=False),
        callback=callback,
    )

    while not result["done"]:
        producer.poll(0.5)

    if result["error"]:
        raise KafkaException(result["error"])


def main():
    global valid_count, invalid_count

    consumer.subscribe([INPUT_TOPIC])

    print(f"Validating messages from {INPUT_TOPIC}")
    print(f"Valid messages -> {VALID_TOPIC}")
    print(f"Invalid messages -> {DLQ_TOPIC}")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            message = consumer.poll(1.0)

            if message is None:
                continue

            if message.error():
                print("Kafka consumer error:", message.error())
                continue

            key = message.key().decode("utf-8") if message.key() else None

            try:
                claim = json.loads(message.value().decode("utf-8"))
                errors = validate_claim(claim)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                claim = {
                    "raw_message": message.value().decode(
                        "utf-8", errors="replace"
                    )
                }
                errors = [f"Invalid JSON message: {exc}"]

            if errors:
                output = {
                    "claim": claim,
                    "validation_errors": errors,
                    "source_topic": message.topic(),
                    "source_partition": message.partition(),
                    "source_offset": message.offset(),
                }

                deliver_and_wait(DLQ_TOPIC, key, output)
                invalid_count += 1
                print(
                    f"INVALID -> DLQ | key={key} | "
                    f"errors={'; '.join(errors)}"
                )
            else:
                deliver_and_wait(VALID_TOPIC, key, claim)
                valid_count += 1
                print(f"VALID -> claims.valid | key={key}")

            # Commit only after the output message is acknowledged.
            consumer.commit(message=message, asynchronous=False)

            if (valid_count + invalid_count) % 100 == 0:
                print(
                    f"Processed: {valid_count + invalid_count} | "
                    f"valid: {valid_count} | invalid: {invalid_count}"
                )

    except KeyboardInterrupt:
        print("\nStopping validation...")
    finally:
        producer.flush(10)
        consumer.close()
        print(f"Valid claims processed: {valid_count}")
        print(f"Invalid claims processed: {invalid_count}")


if __name__ == "__main__":
    main()
