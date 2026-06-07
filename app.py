from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, g, jsonify, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "brokstal_reputation.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = "brokstal-mvp-demo"

SEED_APPEALS = [
    {
        "source": "Яндекс Карты",
        "author": "Алексей К.",
        "rating": 2,
        "tone": "negative",
        "category": "Очередь",
        "priority": "high",
        "status": "new",
        "text": "Долго ждал приём металлолома, очередь почти не двигалась. Хотелось бы быстрее и понятнее по времени.",
        "answer": "Добрый день! Спасибо за обратную связь. Передали информацию ответственному за приёмный пункт, усилим контроль очереди в часы пик.",
    },
    {
        "source": "2ГИС",
        "author": "Марина",
        "rating": 5,
        "tone": "positive",
        "category": "Сервис",
        "priority": "low",
        "status": "answered",
        "text": "Вежливо объяснили порядок приёма, быстро оформили документы. Всё устроило.",
        "answer": "Благодарим за отзыв! Рады, что обслуживание было удобным.",
    },
    {
        "source": "VK",
        "author": "Игорь Петров",
        "rating": 3,
        "tone": "neutral",
        "category": "Вопрос",
        "priority": "medium",
        "status": "in_work",
        "text": "Подскажите, принимаете ли цветной металл в субботу и какие документы нужны физлицу?",
        "answer": "Здравствуйте! Информацию уточняем у ответственного сотрудника и вернёмся с ответом.",
    },
    {
        "source": "Сайт",
        "author": "ООО Альфа",
        "rating": 4,
        "tone": "neutral",
        "category": "Заявка",
        "priority": "medium",
        "status": "new",
        "text": "Нужен расчёт стоимости партии металлопроката и условия доставки по Республике Марий Эл.",
        "answer": "",
    },
    {
        "source": "Яндекс Карты",
        "author": "Дмитрий",
        "rating": 1,
        "tone": "negative",
        "category": "Качество сервиса",
        "priority": "critical",
        "status": "new",
        "text": "Не смог дозвониться несколько раз, потом приехал и снова долго ждал консультации.",
        "answer": "Добрый день! Приносим извинения за ситуацию. Передали обращение руководителю отдела продаж для проверки графика обработки звонков.",
    },
]

STATUS_LABELS = {
    "new": "Новое",
    "in_work": "В работе",
    "answered": "Ответ отправлен",
    "closed": "Закрыто",
}

TONE_LABELS = {
    "negative": "Негативное",
    "neutral": "Нейтральное",
    "positive": "Позитивное",
}

PRIORITY_LABELS = {
    "low": "Низкий",
    "medium": "Средний",
    "high": "Высокий",
    "critical": "Критический",
}


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception: Exception | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    connection = sqlite3.connect(DB_PATH)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS appeals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            author TEXT NOT NULL,
            rating INTEGER NOT NULL,
            tone TEXT NOT NULL,
            category TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT NOT NULL,
            text TEXT NOT NULL,
            answer TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    count = connection.execute("SELECT COUNT(*) FROM appeals").fetchone()[0]
    if count == 0:
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        for item in SEED_APPEALS:
            connection.execute(
                """
                INSERT INTO appeals
                (source, author, rating, tone, category, priority, status, text, answer, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["source"],
                    item["author"],
                    item["rating"],
                    item["tone"],
                    item["category"],
                    item["priority"],
                    item["status"],
                    item["text"],
                    item["answer"],
                    now,
                    now,
                ),
            )
    connection.commit()
    connection.close()


def fetch_appeals() -> list[sqlite3.Row]:
    return get_db().execute("SELECT * FROM appeals ORDER BY id DESC").fetchall()


def build_stats(appeals: list[sqlite3.Row]) -> dict[str, Any]:
    total = len(appeals)
    negative = sum(1 for item in appeals if item["tone"] == "negative")
    in_work = sum(1 for item in appeals if item["status"] in {"new", "in_work"})
    average_rating = round(sum(item["rating"] for item in appeals) / total, 1) if total else 0
    return {
        "total": total,
        "negative": negative,
        "in_work": in_work,
        "average_rating": average_rating,
    }


@app.context_processor
def inject_labels() -> dict[str, Any]:
    return {
        "status_labels": STATUS_LABELS,
        "tone_labels": TONE_LABELS,
        "priority_labels": PRIORITY_LABELS,
    }


@app.route("/")
def index():
    appeals = fetch_appeals()
    return render_template("index.html", appeals=appeals, stats=build_stats(appeals), active="dashboard")


@app.route("/analytics")
def analytics():
    appeals = fetch_appeals()
    by_source = {}
    by_tone = {}
    for item in appeals:
        by_source[item["source"]] = by_source.get(item["source"], 0) + 1
        by_tone[item["tone"]] = by_tone.get(item["tone"], 0) + 1
    return render_template(
        "analytics.html",
        appeals=appeals,
        stats=build_stats(appeals),
        by_source=by_source,
        by_tone=by_tone,
        active="analytics",
    )


@app.route("/appeal/<int:appeal_id>", methods=["GET", "POST"])
def appeal_detail(appeal_id: int):
    db = get_db()
    if request.method == "POST":
        status = request.form.get("status", "in_work")
        answer = request.form.get("answer", "")
        updated_at = datetime.now().strftime("%d.%m.%Y %H:%M")
        db.execute(
            "UPDATE appeals SET status = ?, answer = ?, updated_at = ? WHERE id = ?",
            (status, answer, updated_at, appeal_id),
        )
        db.commit()
        return redirect(url_for("appeal_detail", appeal_id=appeal_id))
    appeal = db.execute("SELECT * FROM appeals WHERE id = ?", (appeal_id,)).fetchone()
    if appeal is None:
        return redirect(url_for("index"))
    return render_template("detail.html", appeal=appeal, active="dashboard")


@app.route("/appeal/new", methods=["POST"])
def create_appeal():
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    get_db().execute(
        """
        INSERT INTO appeals
        (source, author, rating, tone, category, priority, status, text, answer, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 'new', ?, '', ?, ?)
        """,
        (
            request.form.get("source", "Сайт"),
            request.form.get("author", "Пользователь"),
            int(request.form.get("rating", 3)),
            request.form.get("tone", "neutral"),
            request.form.get("category", "Обращение"),
            request.form.get("priority", "medium"),
            request.form.get("text", ""),
            now,
            now,
        ),
    )
    get_db().commit()
    return redirect(url_for("index"))

@app.route("/appeal/delete/<int:appeal_id>", methods=["POST"])
def delete_appeal(appeal_id: int):
    db = get_db()
    db.execute("DELETE FROM appeals WHERE id = ?", (appeal_id,))
    db.commit()
    return redirect(url_for("index"))


@app.route("/api/appeals")
def api_appeals():
    return jsonify([dict(row) for row in fetch_appeals()])


init_db()

if __name__ == "__main__":
    app.run(debug=True)
