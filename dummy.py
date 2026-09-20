from app.agent.graph import build_agent_graph

itinerary_graph = build_agent_graph()

initial_state = {
    "messages": [],
    "destination": "Paris",
    "days": 3,
    "budget": 1500,
    "trip_style": "relaxed",
    "itinerary": None,
}

result = itinerary_graph.invoke(initial_state)

print("Final itinerary:", result.get("itinerary"))
print("\nFull message trace:")
for msg in result["messages"]:
    print(f"- {type(msg)._name_}: {getattr(msg, 'content', '')[:200]}")