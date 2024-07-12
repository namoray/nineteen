import streamlit as st
import pandas as pd
from core.logging import get_logger
from redis.asyncio import Redis
from vali_new.core.store_synthetic_data.synthetic_generations import patched_update_synthetic_data
import asyncio
st.markdown("# Vision [τ, τ] SN19 - Dev Panel")
df = pd.DataFrame({"col": [1, 2, 3], "col2": [4, 5, 6]})

st.write(df)

logger = get_logger(__name__)


@st.cache_resource
def get_redis():
    return Redis(host="localhost", port=6379, db=0)


async def run_with_redis(func, *args, **kwargs):
    redis = get_redis()
    try:
        return await func(redis, *args, **kwargs)
    finally:
        await redis.aclose()

log_display = st.empty()

if st.button("Run Update Synthetic Data"):
    with st.echo():
        result = asyncio.run(run_with_redis(patched_update_synthetic_data))

