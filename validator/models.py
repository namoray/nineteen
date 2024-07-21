from collections import defaultdict


from pydantic import BaseModel, Field
from core import Task
from typing import Optional
from datetime import datetime

task_data = defaultdict(lambda: defaultdict(list))

AxonUID = int


class PeriodScore(BaseModel):
    hotkey: str
    period_score: Optional[float]
    consumed_volume: float
    created_at: datetime


class Participant(BaseModel):
    class Config:
        arbitrary_types_allowed = True
        # Deprecated?
        # allow_mutation = True

    miner_hotkey: str
    task: Task
    synthetic_requests_still_to_make: int = Field(..., description="Synthetic requests still to make")
    delay_between_synthetic_requests: float = Field(..., description="Delay between synthetic requests")
    raw_capacity: float = Field(0, description="Raw capacity straight from the miner")
    capacity: float = Field(..., description="Declared volume for the UID")
    consumed_capacity: float = Field(0, description="Queried volume for the UID")
    capacity_to_score: float = Field(0, description="Volume to score")
    total_requests_made: int = Field(0, description="Total requests made")
    requests_429: int = Field(0, description="HTTP 429 requests")
    requests_500: int = Field(0, description="HTTP 500 requests")
    period_score: Optional[float] = Field(None, description="Period score")

    @property
    def id(self) -> str:
        participant_id = self.miner_hotkey + "-" + self.task.value
        return participant_id

    def calculate_period_score(self) -> float:
        """
        Calculate a period score (not including quality which is scored separately)

        The closer we are to max volume used, the more forgiving we can be.
        For example, if you rate limited me loads (429), but I got most of your volume,
        then fair enough, perhaps I was querying too much

        But if I barely queried your volume, and you still rate limited me loads (429),
        then you're very naughty, you.
        """
        if self.total_requests_made == 0 or self.capacity == 0:
            return None

        self.capacity = max(self.capacity, 1)
        volume_unqueried = max(self.capacity - self.consumed_capacity, 0)

        percentage_of_volume_unqueried = volume_unqueried / self.capacity
        percentage_of_429s = self.requests_429 / self.total_requests_made
        percentage_of_500s = self.requests_500 / self.total_requests_made
        percentage_of_good_requests = (
            self.total_requests_made - self.requests_429 - self.requests_500
        ) / self.total_requests_made

        rate_limit_punishment_factor = percentage_of_429s * percentage_of_volume_unqueried
        server_error_punishment_factor = percentage_of_500s * percentage_of_volume_unqueried

        self.period_score = max(
            percentage_of_good_requests * (1 - rate_limit_punishment_factor) * (1 - server_error_punishment_factor), 0
        )


class RewardData(BaseModel):
    id: str
    task: str
    axon_uid: int
    quality_score: float
    validator_hotkey: str
    miner_hotkey: str
    synthetic_query: bool
    speed_scoring_factor: Optional[float] = None
    response_time: Optional[float] = None
    volume: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.now)

    def dict(self):
        return {
            "id": self.id,
            "task": self.task,
            "axon_uid": self.axon_uid,
            "quality_score": self.quality_score,
            "validator_hotkey": self.validator_hotkey,
            "miner_hotkey": self.miner_hotkey,
            "synthetic_query": self.synthetic_query,
            "speed_scoring_factor": self.speed_scoring_factor,
            "response_time": self.response_time,
            "volume": self.volume,
            "created_at": self.created_at.isoformat(),  # Convert datetime to ISO string
        }
