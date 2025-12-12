from flask import Flask, jsonify, request
import random
import time

app = Flask(__name__)


class RPGSimulation:
    """Handles the logic for the RPG simulation."""

    def __init__(self):
        self.log = []
        self.events = {
            "monster": self._monster_event,
            "treasure": self._treasure_event,
            "trap": self._trap_event,
        }

    def _monster_event(self):
        monster = random.choice(["Goblin", "Orc", "Slime"])
        self.log.append(f"A wild {monster} appears!")
        action = random.choice(["attacks", "casts a spell on"])
        self.log.append(f"The hero {action} the {monster}.")
        if random.random() > 0.3:
            self.log.append(f"The {monster} is defeated!")
        else:
            self.log.append(f"The {monster} evades the attack!")

    def _treasure_event(self):
        item = random.choice(
            ["a healing potion", "a shiny sword", "an old map"])
        self.log.append(f"The hero finds a treasure chest containing {item}!")

    def _trap_event(self):
        trap = random.choice(["a pitfall", "a poison dart", "a magical curse"])
        self.log.append(
            f"The hero encounters {trap} but skillfully avoids it.")

    def run(self, turns: int) -> str:
        """Runs the simulation for a given number of turns."""
        self.log.append("⚔️ Welcome to the AI-Powered RPG Arena! ⚔️\n")
        self.log.append("The simulation is starting...")
        time.sleep(1)  # Simulate a short delay for effect

        for i in range(1, turns + 1):
            self.log.append(f"\n--- Turn {i} ---")
            event_type = random.choice(list(self.events.keys()))
            self.events[event_type]()
            time.sleep(0.5)  # Simulate processing for each turn

        self.log.append("\n\n--- Simulation Complete ---")
        return "\n".join(self.log)


def run_rpg_simulation(turns: int) -> str:
    """A simple placeholder for an AI-powered RPG simulation."""
    simulation = RPGSimulation()
    return simulation.run(turns)


@app.route('/api/game-arena')
def game_arena():
    """API endpoint to run the RPG simulation."""
    turns_str = request.args.get('turns')
    try:
        # Validate that turns is an integer between 1 and 50
        turns = int(turns_str)
        if not 1 <= turns <= 50:
            raise ValueError("Number of turns must be between 1 and 50.")
        output = run_rpg_simulation(turns)
        return jsonify({"success": True, "output": output})
    except (TypeError, ValueError) as e:
        # Handle cases where 'turns' is not a valid integer or is out of range
        return jsonify({"success": False, "error": str(e)}), 400
