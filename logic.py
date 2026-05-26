import asyncio
import random
from typing import List, Dict
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

app = FastAPI(
    title="Digital Library Core API",
    description="Микросервис управления цифровым фондом учебных материалов и автоматического трекинга выдачи",
    version="1.0.0"
)

# --- МОДЕЛИ ДАННЫХ (Pydantic) ---

class Material(BaseModel):
    isbn: str = Field(description="Уникальный международный индекс книги/пособия")
    title: str = Field( description="Название материала")
    author: str = Field(description="Автор или кафедра-составитель")
    pages: int = Field( description="Количество страниц")

class StudentSubscriptionResponse(BaseModel):
    student_id: int
    active_loans_count: int
    has_overdue_materials: bool
    total_estimated_reading_time_hours: float


class AvailabilityResponse(BaseModel):
    isbn: str
    status: str = Field(
        description="Статус доступности материала",
        examples=["AVAILABLE", "RESERVED", "DISTRIBUTED"]
    )
    available_copies: int
    load_factor: float = Field(
        description="Коэффициент востребованности материала студентами (0.0 - 1.0)"
    )

# --- ИМИТАЦИЯ БАЗЫ ДАННЫХ В ОПЕРАТИВКЕ ---

STUDENT_SUBSCRIPTIONS: Dict[int, List[Material]] = {
    202601: [
        Material(isbn="978-5-97060-942-2", title="Асинхронное программирование на Python", author="А. Кленин",
                 pages=340),
        Material(isbn="978-5-9651-1254-8", title="Сетевые протоколы и конфигурирование Windows", author="Д. Ронинова",
                 pages=412)
    ],
    202602: [
        Material(isbn="978-5-99074-233-1", title="Руководство по Docker для системных инженеров", author="М. Власов",
                 pages=210)
    ]
}


# --- ВСПОМОГАТЕЛЬНЫЕ АСИНХРОННЫЕ ФУНКЦИИ ---

async def calculate_storage_load(isbn: str) -> int:
    """Имитация асинхронного подсчета доступных физических и цифровых копий на серверах хранения"""
    await asyncio.sleep(random.uniform(0.1, 0.3))  # Имитируем пинг до распределенного хранилища

    known_isbns = ["978-5-97060-942-2", "978-5-9651-1254-8", "978-5-99074-233-1"]
    if isbn not in known_isbns:
        raise HTTPException(status_code=404, detail=f"Материал с индексом {isbn} отсутствует в реестре фонда")

    # Возвращаем случайное количество доступных лицензий на лету
    return random.randint(0, 15)


# --- ЭНДПОИНТЫ API ---

@app.get("/", tags=["Системные"])
async def root():
    """Проверка статуса микросервиса цифровой библиотеки"""
    return {"status": "active", "subsystem": "Library Core v1", "storage_node": "Node_Central_Connected"}


@app.get("/api/v1/students/{student_id}/subscription", response_model=StudentSubscriptionResponse,
         tags=["Студенческий абонемент"])
async def get_student_subscription_analytics(student_id: int):
    """
    Рассчитывает аналитику по взятым учебным материалам конкретного студента.
    Проверяет загруженность и вычисляет примерное время на освоение книг.
    """
    if student_id not in STUDENT_SUBSCRIPTIONS:
        raise HTTPException(status_code=404, detail="Студент или активный абонемент не найден в базе данных")

    materials = STUDENT_SUBSCRIPTIONS[student_id]
    total_pages = sum(mat.pages for mat in materials)

    # Средняя скорость чтения технического текста — примерно 20 страниц в час
    estimated_time = total_pages / 20.0

    # Имитируем случайное наличие просроченных книг для демонстрации булевой логики
    has_overdue = random.choice([True, False])

    return StudentSubscriptionResponse(
        student_id=student_id,
        active_loans_count=len(materials),
        has_overdue_materials=has_overdue,
        total_estimated_reading_time_hours=round(estimated_time, 2)
    )


@app.post("/api/v1/students/{student_id}/borrow", tags=["Студенческий абонемент"])
async def borrow_material(student_id: int, material: Material):
    """Добавляет учебный материал в абонемент студента (выдача книги)"""
    if student_id not in STUDENT_SUBSCRIPTIONS:
        STUDENT_SUBSCRIPTIONS[student_id] = []

    # Проверяем, есть ли вообще лицензии на этот ISBN в хранилище перед выдачей
    await calculate_storage_load(material.isbn)

    STUDENT_SUBSCRIPTIONS[student_id].append(material)
    return {"status": "success", "message": f"Материал '{material.title}' успешно закреплен за студентом {student_id}"}


@app.get("/api/v1/materials/availability", response_model=List[AvailabilityResponse], tags=["Фонд и Аналитика"])
async def check_materials_availability(
        isbns: List[str] = Query(default=["978-5-97060-942-2"], description="Список ISBN для проверки доступности")
):
    """
    Опрашивает серверы хранения для пачки ISBN.
    Возвращает статус доступности материалов и коэффициент их востребованности.
    """
    results = []

    for isbn in isbns:
        # Проверяем наличие в распределенном хранилище
        copies = await calculate_storage_load(isbn)

        status = "AVAILABLE" if copies > 0 else "DISTRIBUTED"
        load_factor = random.uniform(0.3, 0.95)

        results.append(AvailabilityResponse(
            isbn=isbn,
            status=status,
            available_copies=copies,
            load_factor=round(load_factor, 2)
        ))

    return results