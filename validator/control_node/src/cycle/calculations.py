# Schema for the db


from core import tasks_config as tcfg
from validator.db.src import functions as db_functions
from validator.db.src.database import PSQLDB
from validator.db.src.sql.contenders import fetch_hotkey_scores_for_task
from validator.models import Contender, PeriodScore
from validator.models import RewardData
from fiber.logging_utils import get_logger


logger = get_logger(__name__)

PERIOD_SCORE_TIME_DECAYING_FACTOR = 0.5


async def _get_reward_datas(psql_db: PSQLDB, contender: Contender) -> list[RewardData]:
    async with await psql_db.connection() as connection:
        reward_datas = await db_functions.fetch_recent_most_rewards_for_uid(connection, contender.task, contender.node_hotkey)
    return reward_datas


async def _get_period_scores(psql_db: PSQLDB, contender: Contender) -> list[PeriodScore]:
    async with await psql_db.connection() as connection:
        period_scores = await fetch_hotkey_scores_for_task(connection, contender.task, contender.node_hotkey)
    return period_scores


async def _calculate_combined_quality_score(psql_db: PSQLDB, contender: Contender) -> float:
    reward_datas: list[RewardData] = await _get_reward_datas(psql_db, contender=contender)
    combined_quality_scores = [reward_data.quality_score ** 1.5 * reward_data.speed_scoring_factor for reward_data in reward_datas]
    if not combined_quality_scores:
        return 0
    return sum(combined_quality_scores) / len(combined_quality_scores)


async def _calculate_normalised_period_score(psql_db: PSQLDB, contender: Contender) -> float:
    period_scores = await _get_period_scores(psql_db, contender)
    all_period_scores = [ps for ps in period_scores if ps.period_score is not None]
    normalised_period_scores = _normalise_period_scores(all_period_scores)
    return normalised_period_scores


def _normalise_period_scores(period_scores: list[PeriodScore]) -> float:
    if len(period_scores) == 0:
        return 0

    sum_of_volumes = sum(ps.consumed_capacity for ps in period_scores)
    if sum_of_volumes == 0:
        return 0

    total_score = 0
    total_weight = 0
    for i, score in enumerate(period_scores):
        volume_weight = score.consumed_capacity / sum_of_volumes
        time_weight = (1 - PERIOD_SCORE_TIME_DECAYING_FACTOR) ** i
        combined_weight = volume_weight * time_weight
        if score.period_score is not None:
            total_score += score.period_score * combined_weight
            total_weight += combined_weight
        

    if total_weight == 0:
        return 0
    else:
        return total_score / total_weight


def _calculate_hotkey_effective_volume_for_task(
    combined_quality_score: float, normalised_period_score: float, volume: float
) -> float:
    return combined_quality_score * normalised_period_score * volume


async def _calculate_effective_volumes_for_task(psql_db: PSQLDB, contenders: list[Contender], task: str) -> dict[str, float]:
    hotkey_to_effective_volumes: dict[str, float] = {}
    combined_quality_scores = {}
    normalised_period_scores = {}
    for contender in [i for i in contenders if i.task == task]:
        combined_quality_score = await _calculate_combined_quality_score(psql_db, contender)
        normalised_period_score = await _calculate_normalised_period_score(psql_db, contender)
        effective_volume = _calculate_hotkey_effective_volume_for_task(
            combined_quality_score, normalised_period_score, contender.capacity
        )
        hotkey_to_effective_volumes[contender.node_hotkey] = effective_volume
        combined_quality_scores[contender.node_hotkey] = combined_quality_score
        normalised_period_scores[contender.node_hotkey] = normalised_period_score
    
    logger.debug(f"Combined quality scores: {combined_quality_scores}")
    logger.debug(f"Normalised period scores: {normalised_period_scores}")
    logger.debug(f"Effective volumes: {hotkey_to_effective_volumes}")
    return hotkey_to_effective_volumes


def _normalize_scores_for_task(effective_volumes: dict[str, float]) -> dict[str, float]:
    sum_of_effective_volumes = sum(effective_volumes.values())
    if sum_of_effective_volumes == 0:
        return {}
    return {hotkey: volume / sum_of_effective_volumes for hotkey, volume in effective_volumes.items()}


def _apply_non_linear_transformation(scores: dict[str, float]) -> dict[str, float]:
    return {hotkey: score**4 for hotkey, score in scores.items()}


async def calculate_scores_for_settings_weights(
    psql_db: PSQLDB,
    contenders: list[Contender],
) -> tuple[list[int], list[float]]:
    total_hotkey_scores: dict[str, float] = {}

    for task, config in tcfg.TASK_TO_CONFIG.items():
        if not config.enabled:
            logger.debug(f"Skipping task: {task} as it is not enabled")
            continue
        task_weight = config.weight
        logger.debug(f"Processing task: {task}, weight: {task_weight}\n")

        effective_volumes = await _calculate_effective_volumes_for_task(psql_db, contenders, task.value)
        normalised_scores_before_non_linear = _normalize_scores_for_task(effective_volumes)
        logger.info(f"Normalised scores before non-linear transformation: {normalised_scores_before_non_linear}\n")
        effective_volumes_after_non_linear_transformation = _apply_non_linear_transformation(normalised_scores_before_non_linear)
        normalised_scores_for_task = _normalize_scores_for_task(effective_volumes_after_non_linear_transformation)

        for hotkey, score in normalised_scores_for_task.items():
            total_hotkey_scores[hotkey] = total_hotkey_scores.get(hotkey, 0) + score * task_weight

        logger.debug(f"Completed processing task: {task}")

    logger.debug("Completed calculation of scores for settings weights")

    hotkey_to_uid = {contender.node_hotkey: contender.node_id for contender in contenders}
    total_score = sum(total_hotkey_scores.values())

    node_ids, node_weights = [], []
    for hotkey, score in total_hotkey_scores.items():
        node_ids.append(hotkey_to_uid[hotkey])
        node_weights.append(score / total_score)
    return node_ids, node_weights
