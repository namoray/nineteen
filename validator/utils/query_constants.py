from models import synapses

# Dodgy
OPERATION_TIMEOUTS = {
    "Capacity": 3,
    synapses.TextToImage.__class__.__name__: 10,
    synapses.ImageToImage.__class__.__name__: 10,
    "Chat": 5
}
