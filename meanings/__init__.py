from meanings.house_meanings import HOUSE_MEANINGS

def interpret_house(house_number):
    meaning = HOUSE_MEANINGS.get(house_number)
    if meaning:
        print(f"🏠 {meaning['name']}")
        print(f"Keywords: {', '.join(meaning['keywords'])}")
        print(f"Meaning: {meaning['summary']}")
    else:
        print("Invalid house number.")

# Example
interpret_house(10)
