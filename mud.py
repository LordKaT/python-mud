import time
from server import Server

rooms = {
    "Tavern": {
        "description": "A cozy tavern warmed by an open fire.",
        "exits": {"east": "Main Street"},
    },
    "Main Street": {
        "description": "The main street of town. There's a tavern to the west.",
        "exits": {"west": "Tavern"},
    },
}

players = {}

mud = Server()

while True:
    time.sleep(0.1)
    mud.update()
    for id in mud.get_new_players():
        players[id] = {
            "name": None,
            "room": None,
        }
        mud.send_message(id, "What is your name?")
    
    for id in mud.get_disconnected_players():
        if id not in players:
            continue

        for pid, pl in players.items():
            mud.send_message(pid, f"{players[id]['name']} quit the game")
        
        del(players[id])
    
    for id, command, params in mud.get_commands():
        if id not in players:
            continue
            
        if players[id]["name"] is None:
            players[id]["name"] = command
            players[id]["room"] = "Tavern"

            for pid, pl in players.items():
                mud.send_message(pid, f"{players[id]['name']} entered the game")
            
            mud.send_message(id, f"Welcome to the game {players[id]['name']}")
            mud.send_message(id, rooms[players[id]['room']]["description"])
        
        elif command == "help":
            mud.send_message(id, "Help message here")
        
        elif command == "say":
            for pid, pl in players.items():
                if players[pid]["room"] == players[id]["room"]:
                    mud.send_message(pid, f"{players[id]['name']} says {params}")
        
        elif command == "look":
            rm = rooms[players[id]["room"]]
            mud.send_message(id, rm["description"])
            playershere = []
            for pid, pl in players.items():
                if players[pid]["room"] == players[id]["room"]:
                    if players[pid]["name"] is not None:
                        playershere.append(players[pid]["name"])
            mud.send_message(id, f"Players here {', '.join(playershere)}")
            mud.send_message(id, f"Exits: {', '.join(rm['exits'])}")
        
        elif command == "go" or command == "move" or command == "mv":
            ex = params.lower()
            rm = rooms[players[id]["room"]]
            if ex in rm["exits"]:
                for pid, pl in players.items():
                    if players[pid]["room"] == players[id]["room"] and pid != id:
                        mud.send_message(pid, f"{players[id]['name']} left towards {ex}")
                
                players[id]["room"] = rm["exits"][ex]
                rm = rooms[players[id]["room"]]
                for pid, pl in players.items():
                    if players[pid]["room"] == players[id]["room"] and pid!= id:
                        mud.send_message(pid, f"{players[id]['name']} arrived from {ex}")
                mud.send_message(id, f"You arrived at {players[id]['room']}")
            else:
                mud.send_message(id, f"Unknown exit {ex}")
        
        else:
            mud.send_message(id, f"Unknown command {command}")
