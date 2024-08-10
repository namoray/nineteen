from pydantic import BaseModel
from generic.tasks import Task


class TaskStatsForUID(BaseModel):
    uid: int
    task: Task
    current_volume: float
    quality_score: float
    volume_reliability_score: float
