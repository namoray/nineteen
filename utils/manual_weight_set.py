"""
This is a utility script for manually setting weights in the case of any issues
Use cases:
- Testing weight setting to see scores and help debug
- Emergencies if weight setting in the vali is facing issues - but the proxy is still working as expected [not recommended]

NOTE: this is not artificial weights / weight copying, it uses real values obtained by the validator proxy only.
It's just taking that part of the code, and making it independently runnable

Usage:
python manually_set_weights.py --env_file {youvr_vali_hotkey_env_file_here}
"""

"""
TODO: GET THIS TO WORK WITH DOCKER COMPOSE
"""