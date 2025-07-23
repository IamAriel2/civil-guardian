from shapely.geometry import LineString
from os import path
import json
import osmnx as ox

def street_distance(loc1, loc2):
    return ox.distance.great_circle(lat1=loc1[0], lon1=loc1[1],
                                  lat2=loc2[0], lon2=loc2[1])

def address_to_coords(address):
    try:
        full_address = f"{address}, Holon, Israel"
        location = ox.geocode(full_address)
        return location
        
    except Exception as e:
        print(f"Error converting address '{address}': {e}")
        return None

id = 0
def split_street(G, u, v, key, loc):
    global id
    u_loc = (G.nodes[u]['x'], G.nodes[u]['y'])
    v_loc = (G.nodes[v]['x'], G.nodes[v]['y'])
    shelter_loc = (loc[1], loc[0])

    id += 1
    G.add_node(id, y=loc[0], x=loc[1])
    G.add_edge(u, id, length=street_distance((G.nodes[u]['y'], G.nodes[u]['x']), loc),
               geometry=LineString([u_loc, shelter_loc]))
    G.add_edge(id, v, length=street_distance((G.nodes[v]['y'], G.nodes[v]['x']), loc),
               geometry=LineString([shelter_loc, v_loc]))
    G.remove_edge(u, v, key)
    return id

def add_shelter_nodes(G, shelters):
    shelter_nodes = list()

    for shelter in shelters:
        loc = shelter['coords']
        u, v, key = ox.nearest_edges(G, loc[1], loc[0])
        new_node = split_street(G, u, v, key, loc)
        G.nodes[new_node]['shelter'] = True
        G.nodes[new_node]['name'] = shelter['name']
        shelter_nodes.append(new_node)

    return shelter_nodes

# Proccessing the graph to create circles around shelters
def create_circle_rec(G, node):
    for u, v, data in G.edges(node, data=True): 
        other = u if v == node else v
        remain = G.nodes[node]['rem'] - data['length']

        if remain < G.nodes[other]['rem']:
            continue
        elif remain < data['length']:
            G.nodes[other]['rem'] = 0
        else:
            G.nodes[other]['rem'] = remain
            create_circle_rec(G, other)

def create_circles(G, nodes, radius):
    for node in G.nodes:
        G.nodes[node]['rem'] = 0

    for node in nodes:
        G.nodes[node]['rem'] = radius
        create_circle_rec(G, node)

def calc_lengths(G):
    lengths = {}
    for u, v, key, data in G.edges(keys=True, data=True):
        lengths[f"{u} {v} {key}"] = {"length": data['length']}
        lengths[f"{v} {u} {key}"] = {"length": data['length']}
        if G.nodes[u]["rem"] + G.nodes[v]["rem"] > data['length']:
            lengths[f"{u} {v} {key}"]["rem"] = G.nodes[u]["rem"]
            lengths[f"{v} {u} {key}"]["rem"] = G.nodes[v]["rem"]
        else:
            lengths[f"{u} {v} {key}"]["rem"] = -1
            lengths[f"{v} {u} {key}"]["rem"] = -1
    return lengths

def eval_rem_value(G, node):
    max_rem = 0
    for u, v, data in G.edges(node, data=True):
        other = u if v == node else v
        cur = G.nodes[other]['rem']
        max_rem = max(max_rem, cur)
        
    G.nodes[node]['rem'] = max(max_rem - data['length'], 0)

def add_one_node(G, loc):
    u, v, key = ox.nearest_edges(G, loc[1], loc[0])
    loc = split_street(G, u, v, key, loc)
    eval_rem_value(G, loc)
    return loc

def build_map():
    G = ox.graph_from_place("Holon, Israel", network_type="walk")
    with open("shelters.json", encoding="utf-8") as f:
        shelters = json.load(f)
    RADIUS = float(input("Enter the max distance from a shelter (in meters):"))

    shelter_nodes = add_shelter_nodes(G, shelters)
    create_circles(G, shelter_nodes, RADIUS)
    lengths = calc_lengths(G)

    with open("graph.json", "w") as f:
        json.dump(lengths, f, indent=4)

    print(f"Saved {len(lengths)} edge lengths to graph.json")
    return G

if __name__ == "__main__":
    G = build_map()