"""Seed vocabulary - loaded by a data migration, editable by the user afterward.

Every entry here is a starting point, not a rule: the Settings screen lets the
user rename, archive, or extend all of it (PDD "user-controlled vocabulary").
"""

PLANT_TYPES = [
    "Annual", "Biennial", "Perennial", "Bulb/Corm/Tuber", "Shrub", "Tree",
    "Vine", "Herb", "Vegetable", "Fruit", "Groundcover",
]

BED_TYPES = [
    "Perennial", "Shrub", "Vegetable", "Herb", "Fruit", "Mixed border",
    "Woodland", "Raised bed", "Container area", "Lawn",
]

ACTIVITY_TYPES = [
    # PDD "Record Activity" choices. "Harvested" is deliberately absent -
    # harvests are HarvestEvents with their own structure; the UI routes the
    # Harvested verb to Quick Harvest instead.
    "Pruned", "Fertilized", "Watered", "Sprayed/Treated", "Transplanted",
    "Divided", "Planted", "Mulched", "Pest/Disease Check", "Other",
]

TASK_CATEGORIES = [
    "Pruning", "Fertilizing", "Watering", "Weeding", "Mulching", "Planting",
    "Inspection",
]

HARVEST_UNITS = [
    "fruit", "pounds", "ounces", "baskets", "cups", "bunches", "handfuls",
]

PHOTO_CATEGORIES = [
    # PDD 5.2
    "Whole plant", "Leaves", "Flowers", "Fruit", "Seeds", "Bark/trunk",
    "Branches/stems", "Buds/new growth", "Roots/crown", "Harvest",
    "Pest or disease symptom", "Damage/stress", "Pruning/maintenance",
    "Before treatment", "After treatment", "Other",
]

# (label, start_month, start_day, end_month, end_day)
# Meteorological seasons split into thirds, plus the full seasons. All
# user-editable in Settings; Late winter crossing nothing here because winter
# itself crosses the year boundary (Dec-Feb).
SEASON_WINDOWS = [
    ("Early winter", 12, 1, 12, 31),
    ("Mid winter", 1, 1, 1, 31),
    ("Late winter", 2, 1, 2, 28),
    ("Winter", 12, 1, 2, 28),
    ("Early spring", 3, 1, 3, 31),
    ("Mid spring", 4, 1, 4, 30),
    ("Late spring", 5, 1, 5, 31),
    ("Spring", 3, 1, 5, 31),
    ("Early summer", 6, 1, 6, 30),
    ("Mid summer", 7, 1, 7, 31),
    ("Late summer", 8, 1, 8, 31),
    ("Summer", 6, 1, 8, 31),
    ("Early fall", 9, 1, 9, 30),
    ("Mid fall", 10, 1, 10, 31),
    ("Late fall", 11, 1, 11, 30),
    ("Fall", 9, 1, 11, 30),
]
