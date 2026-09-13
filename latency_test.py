import time

import requests


API_URL = "http://localhost:8000/api/messages"
SENDER_ID = 1
REQUEST_TIMEOUT_SECONDS = 30

TEST_MESSAGES = [
    {"content": "Here are the notes for the EDI project.", "group_muted": False},
    {"content": "URGENT: The submission deadline is tomorrow at 5 PM!", "group_muted": False},
    {"content": "Can we schedule a meeting next week?", "group_muted": True},
    {"content": "Just a routine update for the group.", "group_muted": True},
    {"content": "Critical outage: the server is down right now.", "group_muted": False},
]


def run_latency_test() -> None:
    print("Starting API Latency & Performance Test...\n")
    total_time = 0.0
    completed_requests = 0

    for index, message_data in enumerate(TEST_MESSAGES, start=1):
        payload = {
            "sender_id": SENDER_ID,
            "content": message_data["content"],
            "group_muted": message_data["group_muted"],
        }
        start_time = time.perf_counter()

        try:
            response = requests.post(API_URL, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        except requests.exceptions.RequestException as error:
            print(f"Error: Could not complete request {index}: {error}")
            continue

        latency = (time.perf_counter() - start_time) * 1000
        total_time += latency
        completed_requests += 1
        print(f"Message {index}: '{message_data['content'][:35]}...'")
        print(f"Status: {response.status_code} | Latency: {latency:.2f} ms\n")

    print("-" * 40)
    print(f"Test Completed: {completed_requests}/{len(TEST_MESSAGES)} messages processed.")
    if completed_requests:
        print(f"Average Latency per Message: {total_time / completed_requests:.2f} ms")
        print(f"Total Processing Time: {total_time:.2f} ms")
    else:
        print("No requests completed. Is Uvicorn running on port 8000?")
    print("-" * 40)


if __name__ == "__main__":
    run_latency_test()
