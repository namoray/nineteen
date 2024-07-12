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
    return asyncio.run(run_with_redis(synthetic_generations.get_stored_synthetic_data))


@st.cache_data
def get_participants():
    participants = asyncio.run(run_with_redis(putils.load_participants))
    participants = [{**participant.model_dump(), **{"id": participant.id}} for participant in participants]
    return participants


@st.cache_data
def get_synthetic_query_list():
    participants = asyncio.run(run_with_redis(putils.load_synthetic_query_list))

    return participants


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
################# Top level buttons #######################################
with st.container():
    st.markdown("---")  # Horizontal line above the box
    top_row_col1, top_row_col2 = st.columns(2)

    if "scheduling_active" not in st.session_state:
        st.session_state.scheduling_active = False
    with top_row_col1:
        if st.button("Clear Redis"):
            asyncio.run(run_with_redis(clear_redis))
    with top_row_col2:
        if st.button("Toggle Scheduling"):
            st.session_state.scheduling_active = not st.session_state.scheduling_active
            if st.session_state.scheduling_active:
                st.session_state.scheduling_tasks = asyncio.run(run_with_redis(scheduling_participants.start_scheduling))
            else:
                for task in st.session_state.scheduling_tasks:
                    task.cancel()
                st.session_state.scheduling_tasks = []

        st.write("Scheduling is", "active" if st.session_state.scheduling_active else "inactive")
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
        asyncio.run(run_with_redis(synthetic_generations.patched_update_synthetic_data, task=Task(selected_model)))
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
        asyncio.run(
            run_with_redis(
                get_participant_info.patched_get_and_store_participant_info,
                number_of_participants=number_of_participants,
            )
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
        asyncio.run(run_with_redis(putils.add_participant_to_synthetic_query_list, participant_id))
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
