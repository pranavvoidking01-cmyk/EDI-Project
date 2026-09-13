from datetime import datetime, timedelta, timezone

from backend.main import Message, PriorityLog, SessionLocal, Task, User


GROUPS = [
    (1, "EDI Project"),
    (2, "Design Review"),
    (3, "Study Circle"),
    (4, "Launch Operations"),
    (5, "Campus Community"),
]
MEMBERS = [
    (1, "Local User", "local@example.com"),
    (2, "Maya Khan", "maya@example.com"),
    (3, "Jordan Tan", "jordan@example.com"),
    (4, "Alex Rivera", "alex@example.com"),
    (5, "Priya Shah", "priya@example.com"),
    (6, "Noah Williams", "noah@example.com"),
]


def seed() -> None:
    db = SessionLocal()
    try:
        db.query(PriorityLog).delete()
        db.query(Message).delete()
        db.query(Task).delete()
        for user_id, name, email in MEMBERS:
            user = db.get(User, user_id)
            if user is None:
                db.add(User(id=user_id, name=name, email=email))
            else:
                user.name = name
                user.email = email
        db.commit()

        now = datetime.now(timezone.utc)
        messages = []
        templates = [
            "Shared the latest project notes for review.",
            "The timeline is looking good for this sprint.",
            "Can everyone add their feedback before the meeting?",
            "Reminder: the next check-in is scheduled for tomorrow.",
            "I uploaded the reference documents to the workspace.",
            "Please review the open questions when you have a moment.",
            "The team agreed on the updated workflow.",
            "Here is a quick progress update from my side.",
            "We should align on the final presentation structure.",
            "Thanks everyone for keeping the discussion moving.",
        ]
        alert_templates = {
            0: ("[NLP-ALERT] URGENT: submission deadline is tomorrow at 5 PM.", "[NLP-ALERT] EDI hand-in closes before Friday."),
            1: ("[NLP-ALERT] Critical design blocker needs escalation immediately.", "[NLP-ALERT] Design sign-off is due tonight."),
            2: ("[NLP-ALERT] Exam registration closes before Friday.", "[NLP-ALERT] Study group room changes at 6 PM."),
            3: ("[NLP-ALERT] Production outage requires action now.", "[NLP-ALERT] Deployment rollback deadline is today."),
            4: ("[NLP-ALERT] Emergency campus notice: respond by tonight.", "[NLP-ALERT] Community registration ends tomorrow."),
        }
        for chat_id, _group_name in GROUPS:
            for index in range(10):
                content = alert_templates[chat_id - 1][index - 8] if index >= 8 else templates[index]
                messages.append(
                    Message(
                        group_id=chat_id,
                        sender_id=((chat_id + index) % 6) + 1,
                        content=content,
                        timestamp=now - timedelta(hours=chat_id * 3 + index),
                        status="sent",
                        priority_score=0.95 if index == 8 else 0.2,
                    )
                )
        db.add_all(messages)
        db.commit()
        for message in messages[8::10] + messages[9::10]:
            db.add(
                PriorityLog(
                    message_id=message.id,
                    action="modified" if message.id % 2 else "deleted",
                    previous_content=message.content,
                    original_timestamp=message.timestamp,
                    logged_at=now,
                )
            )
        db.commit()

        task_names = [
            "Math assignment", "EDI submission", "Review wireframes", "Prepare demo script",
            "Book project check-in", "Upload research notes", "Resolve deployment blocker",
            "Draft final presentation", "Confirm team availability", "Submit peer feedback",
        ]
        tasks = [
            Task(
                description=name,
                deadline=now + timedelta(days=index + 1),
                status="done" if index < 2 else ("in-progress" if index < 5 else "todo"),
            )
            for index, name in enumerate(task_names)
        ]
        db.add_all(tasks)
        db.commit()
        print("Seeded 5 chats, 50 messages, 10 tasks, and 10 priority logs.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
