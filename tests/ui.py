from datetime import datetime, timedelta
import os

os.environ["ENV"] = "dev"

from typing import Any, Awaitable, Callable, TypeVar  # noqa
import streamlit as st  # noqa
from core import Task  # noqa
from core.logging import get_logger  # noqa
from redis.asyncio import Redis  # noqa
from vali_new.core.store_synthetic_data import synthetic_generations  # noqa
import asyncio  # noqa
from vali_new.core.manage_participants import get_participant_info, scheduling_participants  # noqa
from vali_new.utils import participant_utils as putils, redis_utils as rutils  # noqa
from vali_new.utils import redis_constants as rcst  # noqa
import pandas as pd  # noqa

pd.set_option("future.no_silent_downcasting", True)

st.set_page_config(layout="wide")
st.markdown("# Vision [τ, τ] SN19 - Dev Panel")


logger = get_logger(__name__)
T = TypeVar("T")


@st.cache_resource
def get_redis():
    return Redis(host="localhost", port=6379, db=0)


@st.cache_data
def get_synthetic_data():
    return run_in_loop(synthetic_generations.get_stored_synthetic_data)


@st.cache_data
def get_synthetic_scheduling_queue():
    return run_in_loop(putils.load_synthetic_scheduling_queue)


@st.cache_data
def get_participants():
    participants = run_in_loop(putils.load_participants)
    participants = [{**participant.model_dump(), **{"id": participant.id}} for participant in participants]
    for participant in participants:
        participant["task"] = participant["task"].value
    return participants


@st.cache_data(ttl=0.1)
def get_query_queue():
    participants = run_in_loop(putils.load_query_queue)

    return participants


@st.cache_resource(show_spinner=True)
def get_event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop


def run_in_loop(
    func: Callable[[Any, Any], Awaitable[T]],
    *args: Any,
    with_redis: bool = True,
    create_task: bool = False,
    **kwargs: Any,
) -> T:
    loop = get_event_loop()

    if create_task:
        if with_redis:
            return loop.create_task(run_with_redis(func, *args, **kwargs))
        else:
            return loop.create_task(func(*args, **kwargs))
    else:
        if with_redis:
            return loop.run_until_complete(run_with_redis(func, *args, **kwargs))
        else:
            return loop.run_until_complete(func(*args, **kwargs))


async def run_with_redis(func: Callable[[Redis, Any, Any], Awaitable[T]], *args: Any, **kwargs: Any) -> T:
    redis = get_redis()
    try:
        return await func(redis, *args, **kwargs)
    finally:
        await redis.aclose()


async def clear_redis(redis_db: Redis):
    await redis_db.flushall()
    st.cache_data.clear()


if "participants_being_scheduled" not in st.session_state:
    st.session_state["participants_being_scheduled"] = {}

####################################################################
################# State #######################################


####################################################################
################# Top level buttons #######################################
with st.container():
    st.markdown("---")  # Horizontal line above the box
    top_row_col1, top_row_col2 = st.columns(2)

    with top_row_col1:
        if st.button("Clear Redis"):
            run_in_loop(clear_redis)

    st.markdown("---")

####################################################################
################# First row #######################################

col1, col2 = st.columns(2)


##########################
### Synthetic Data #######

with col1:
    st.subheader("Synthetic Data Management")

    model_options = [t.value for t in Task]
    selected_model = st.selectbox("Select Model", model_options, index=0)

    if st.button("Add Synthetic Data"):
        run_in_loop(synthetic_generations.patched_update_synthetic_data, task=Task(selected_model))
        st.cache_data.clear()

    synthetic_data = get_synthetic_data()
    if synthetic_data:
        st.write(synthetic_data)

##########################
### Participants #######

with col2:
    st.subheader("Participants Management")

    number_of_participants = st.number_input("Number of participants", min_value=1, value=1)
    if st.button("Add Fake Participants"):
        run_in_loop(
            get_participant_info.patched_get_and_store_participant_info,
            number_of_participants=number_of_participants,
        )

        st.cache_data.clear()

    participants = get_participants()
    edited_participants = st.data_editor(participants, num_rows="dynamic", key="participant_editor")
    if st.button("Save participants"):
        run_in_loop(rutils.delete_key_from_redis, rcst.PARTICIPANT_IDS_KEY)
        for participant in edited_participants:
            run_in_loop(
                get_participant_info.store_participant,
                task=participant["task"],
                hotkey=participant["hotkey"],
                declared_volume=participant["declared_volume"],
                volume_to_score=participant["volume_to_score"],
                synthetic_requests_still_to_make=participant["synthetic_requests_still_to_make"],
                delay_between_synthetic_requests=participant["delay_between_synthetic_requests"],
            )
        st.cache_data.clear()


####################################################################
################# Second row #######################################

##########################
### Scheduling #######
st.markdown("---")
with st.container():
    st.markdown("<h1 style='text-align: center;'>Queues</h1>", unsafe_allow_html=True)

    st.markdown("- - -")
    tc1, tc2 = st.columns(2)

    with tc1:
        participant_id = st.selectbox("Select participant", [participant["id"] for participant in get_participants()])

    with tc2:
        schedule_in_x_seconds = st.number_input("Schedule synthetic query in X seconds", min_value=1, value=1)

    st.markdown("- - -")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Synthetic Scheduling Queue")

        if st.button("Schedule Synthetic Queries for participant"):
            time_to_schedule_for = datetime.now() + timedelta(seconds=schedule_in_x_seconds)
            run_in_loop(
                scheduling_participants.schedule_synthetic_query,
                participant_id,
                timestamp=time_to_schedule_for.timestamp(),
            )
            st.cache_data.clear()

        scheduled_synthetic_queries = get_synthetic_scheduling_queue()

        if scheduled_synthetic_queries:
            st.write(scheduled_synthetic_queries)
    with col2:
        st.subheader("Query queue")

        if st.button("Add synthetic queries which are ready"):
            run_in_loop(putils.add_synthetic_query_to_queue, participant_id)
            st.cache_data.clear()
        synthetic_query_list = get_query_queue()

        if synthetic_query_list:
            st.write(synthetic_query_list)


st.markdown("---")
##########################
### Participants #######

col4, col5 = st.columns(2)
with col4:
    st.header("Ongoing")
    st.subheader("Scheduling")

log_display = st.empty()


# col5, col6 = st.columns(2)

# with col5:
#     st.subheader("Organic Queries")

# with col6:
#     st.subheader("Weight setting")
