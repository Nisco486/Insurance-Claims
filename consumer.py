
import json
from confluent_kafka import Consumer

consumer = Consumer({
    "bootstrap.servers": "localhost:9092",
    "group.id": "insurance-claim-test",
    "auto.offset.reset": "earliest"
})

consumer.subscribe(["insurance-claims"])

print("Consumer started. Waiting for insurance claims...")

try:
    while True:
        message = consumer.poll(1.0)

        if message is None:
            continue

        if message.error():
            print("Kafka error:", message.error())
            continue

        claim = json.loads(message.value().decode("utf-8"))

        print("\nClaim received successfully!")
        print(json.dumps(claim, indent=4))

except KeyboardInterrupt:
    print("\nStopping consumer...")

finally:
    consumer.close()
