import random

# States
WAITING  = "waiting"
NIBBLING = "nibbling"
BITING   = "biting"
CAUGHT   = "caught"
MISSED   = "missed"

# Base transition matrix
# From each state: probabilities to next states
BASE_TRANSITIONS = {
    WAITING: {
        WAITING:  0.6,
        NIBBLING: 0.4,
    },
    NIBBLING: {
        NIBBLING: 0.3,
        BITING:   0.4,
        MISSED:   0.3,
    },
    BITING: {
        BITING:  0.2,
        CAUGHT:  0.6,
        MISSED:  0.2,
    },
}

def get_transition_matrix(depth: float, location_id: int) -> dict:
    """
    Adjust transition probabilities based on depth and location.
    Deeper depth = fish more likely to bite.
    Certain locations have more active fish.
    """
    matrix = {s: dict(v) for s, v in BASE_TRANSITIONS.items()}

    # Depth bonus — deeper means fish are hungrier
    if depth >= 0.7:  # deep zone
        matrix[WAITING][NIBBLING]  += 0.2
        matrix[WAITING][WAITING]   -= 0.2
        matrix[NIBBLING][BITING]   += 0.15
        matrix[NIBBLING][MISSED]   -= 0.15

    elif depth >= 0.35:  # mid zone
        matrix[WAITING][NIBBLING]  += 0.1
        matrix[WAITING][WAITING]   -= 0.1

    # Location bonus
    location_bonuses = {
        1: 0.0,   # Baltic Sea   — normal
        2: 0.05,  # North Sea    — slightly more active
        3: 0.10,  # Caribbean    — warm water, active fish
        4: 0.05,  # Pacific      — normal
        5: 0.15,  # Mariana      — rare but aggressive
    }
    bonus = location_bonuses.get(location_id, 0.0)
    matrix[NIBBLING][BITING]  += bonus
    matrix[NIBBLING][MISSED]  -= bonus

    return matrix

def next_state(current: str, matrix: dict) -> str:
    """Pick next state based on transition probabilities."""
    transitions = matrix.get(current, {})
    states  = list(transitions.keys())
    weights = list(transitions.values())
    return random.choices(states, weights=weights, k=1)[0]

def simulate_catch(depth: float, location_id: int) -> dict:
    """
    Simulate the Markov chain from WAITING until terminal state.
    Returns the final state and number of steps taken.
    """
    matrix = get_transition_matrix(depth, location_id)
    state  = WAITING
    steps  = 0
    path   = [state]

    while state not in (CAUGHT, MISSED):
        state = next_state(state, matrix)
        path.append(state)
        steps += 1
        if steps > 20:  # safety cap
            state = MISSED
            break

    return {
        "final_state": state,
        "steps":       steps,
        "path":        path,
        "caught":      state == CAUGHT,
    }