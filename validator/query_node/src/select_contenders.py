import math
import random
from typing import Optional

from asyncpg import Connection

from validator.db.src.sql.contenders import get_contenders_for_selection
from validator.models import Contender, ContenderSelectionInfo

WEIGHT_QUALITY_SCORE=1.0
WEIGHT_PERIOD_SCORE=0.7
SOFTMAX_TEMPERATURE=2.0


def weighted_random_sample_without_replacement(contenders: list[ContenderSelectionInfo], probabilities: list[float], k: int) -> list[ContenderSelectionInfo]:
    if contenders is None or len(contenders) == 0:
        return []
    selected = []
    for _ in range(k):
        selected_index = random.choices(range(len(probabilities)), weights=probabilities, k=1)[0]
        selected.append(contenders[selected_index])
        del contenders[selected_index]
        del probabilities[selected_index]
    return selected


def _softmax(scores: list[float], temperature: Optional[float] = None) -> list[float]:
    """
    Compute the softmax of scores. Temperature is used to scale the scores
    so that there is a chance for the lower scores to be selected.
    It also converts the scores to probabilities that sum to 1
    """
    if temperature is None:
        temperature = SOFTMAX_TEMPERATURE

    if scores is None or len(scores) == 0:
        return []
    x = [xi / temperature for xi in scores]
    max_x = max(x)
    e_x = [math.exp(xi - max_x) for xi in x]
    sum_e_x = sum(e_x)
    return [ei / sum_e_x for ei in e_x]

def _normalize_scores_for_selection(scores: list[float]) -> list[float]:
    if scores is None or len(scores) == 0:
        return []
    max_score = max(scores)
    min_score = min(scores)

    if max_score == min_score:
        return [0.0] * len(scores)

    return [(score - min_score) / (max_score - min_score) for score in scores]


##########################################################
async def select_contenders(connection: Connection, task: str, top_x: int = 5) -> list[Contender]:
    contenders_for_selection = await get_contenders_for_selection(connection, task)
    if len(contenders_for_selection) <= 1:
        return [contender.to_contender_model() for contender in contenders_for_selection]

    # extract params
    last_quality_scores = [0.0 if contender.last_combined_quality_score is None else contender.last_combined_quality_score
                           for contender in contenders_for_selection]
    current_period_scores = [0.0 if contender.period_score is None else contender.period_score
                             for contender in contenders_for_selection]

    # normalize scores
    normalized_last_quality_scores = _normalize_scores_for_selection(last_quality_scores)
    normalized_current_period_scores = _normalize_scores_for_selection(current_period_scores)

    composite_scores = [WEIGHT_QUALITY_SCORE * this_quality_score + WEIGHT_PERIOD_SCORE * this_period_score
                        for this_quality_score, this_period_score
                        in zip(normalized_last_quality_scores, normalized_current_period_scores)]

    probabilities = _softmax(composite_scores)
    final_selection = weighted_random_sample_without_replacement(contenders_for_selection, probabilities, top_x)

    return [selected_contender.to_contender_model() for selected_contender in final_selection]