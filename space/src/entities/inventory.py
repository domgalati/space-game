class Inventory:
    """Item ids (world.items) and how many of each, up to a total capacity."""

    def __init__(self, capacity):
        self.capacity = capacity
        self.items = {}

    def add_item(self, item, quantity):
        if self.get_total_quantity() + quantity > self.capacity:
            return False  # Inventory full
        self.items[item] = self.items.get(item, 0) + quantity
        return True

    def remove_item(self, item, quantity):
        if self.items.get(item, 0) < quantity:
            return False  # Not enough items
        self.items[item] -= quantity
        if self.items[item] == 0:
            del self.items[item]
        return True

    def to_dict(self):
        return {"capacity": self.capacity, "items": dict(self.items)}

    @classmethod
    def from_dict(cls, data):
        inventory = cls(data["capacity"])
        inventory.items = dict(data.get("items") or {})
        return inventory

    def get_total_quantity(self):
        return sum(self.items.values())

    def __str__(self):
        return f"Inventory({self.items}, Capacity: {self.capacity})"
