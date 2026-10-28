
import json
from confluent_kafka import Producer

producer = Producer({
    "bootstrap.servers": "localhost:9092",
    "enable.idempotence": True
})

claim = {
    "claim_id": "CLM001",
    "patient_id": "PAT101",
    "hospital_id": "HOSP101",
    "agent_id": "AGENT01",
    "claim_amount_requested_inr": 85000,
    "procedure_code": "99213",
    "date_of_claim": "2026-10-10",
    "claim_status": "SUBMITTED"
}

def delivery_report(error, message):
    if error:
        print(f"Delivery failed: {error}")
    else:
        print(
            f"Claim {claim['claim_id']} delivered to "
            f"{message.topic()}, partition={message.partition()}, "
            f"offset={message.offset()}"
        )

try:
    producer.produce(
        topic="insurance-claims",
        key=claim["hospital_id"],
        value=json.dumps(claim),
        callback=delivery_report
    )

    remaining = producer.flush(10)

    if remaining:
        print(f"Warning: {remaining} message(s) remain undelivered.")

except Exception as error:
    print("Producer error:", error)
