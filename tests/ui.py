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
def get_participants():
    participants = run_in_loop(putils.load_participants)
    participants = [{**participant.model_dump(), **{"id": participant.id}} for participant in participants]
    return participants


@st.cache_data
def get_synthetic_query_list():
    participants = run_in_loop(putils.load_synthetic_query_list)

    return participants


@st.cache_resource(show_spinner=True)
def get_event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop


def run_in_loop(func: Callable[[Any, Any], Awaitable[T]], with_redis: bool = True, *args: Any, **kwargs: Any) -> T:
    loop = get_event_loop()
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


####################################################################
################# State #######################################
if "scheduling_active" not in st.session_state:
    st.session_state.scheduling_active = False
if "participants_being_scheduled" not in st.session_state:
    st.session_state.participants_being_scheduled = {}


####################################################################
################# Top level buttons #######################################
with st.container():
    st.markdown("---")  # Horizontal line above the box
    top_row_col1, top_row_col2 = st.columns(2)

    with top_row_col1:
        if st.button("Clear Redis"):
            run_in_loop(clear_redis)
    with top_row_col2:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Toggle Scheduling for all participants"):
                st.session_state.scheduling_active = not st.session_state.scheduling_active
                if st.session_state.scheduling_active:
                    st.session_state.scheduling_tasks = run_in_loop(scheduling_participants.start_scheduling)

                else:
                    logger.debug("Cancelling scheduling tasks")
                    for task in st.session_state.scheduling_tasks:
                        task.cancel()
                    st.session_state.scheduling_tasks = []
            st.write("Scheduling is", "active" if st.session_state.scheduling_active else "inactive")
        with c2:
            participant_id = st.selectbox(
                "Select participant", [participant["id"] for participant in get_participants()], key="toplevel"
            )

            if st.button(f"Toggle scheduling for participant: {participant_id}"):
                if participant_id in st.session_state.participants_being_scheduled:
                    task = st.session_state.participants_being_scheduled.pop(participant_id)
                    task.cancel()
                else:
                    scheduling_task = run_in_loop(
                        scheduling_participants.handle_scheduling_for_participant, participant_id
                    )

                    st.session_state.participants_being_scheduled[participant_id] = scheduling_task

            st.write(
                f"Scheduling for {participant_id} is",
                "active" if participant_id in st.session_state.participants_being_scheduled else "inactive",
            )

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
    st.write(participants)


####################################################################
################# Second row #######################################

col3, col4 = st.columns(2)

##########################
### Scheduling #######

with col3:
    st.subheader("Scheduling")

    participant_id = st.selectbox("Select participant", [participant["id"] for participant in get_participants()])

    if st.button("Schedule participant for synthetic request"):
        run_in_loop(putils.add_participant_to_synthetic_query_list, participant_id)
        st.cache_data.clear()
    synthetic_query_list = get_synthetic_query_list()

    if synthetic_query_list:
        st.write(synthetic_query_list)

##########################
### Participants #######

with col4:
    st.subheader("On going queries")
log_display = st.empty()


col5, col6 = st.columns(2)

with col5:
    st.subheader("Organic Queries")

with col6:
    st.subheader("Weight setting")
