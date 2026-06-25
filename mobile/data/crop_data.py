"""
Crop catalogue with sub-titles.
Used to populate the editable dropdown on the Collect Data screen.
"""

CROP_CATEGORIES = {
    "Cereals": [
        "Rice", "Sorghum", "Rabi Sorghum", "Maize",
        "Pearl Millet", "Finger Millet", "Little Millet",
        "Kodo Millet", "Proso Millet", "Barnyard Millet",
        "Browntop Millet", "Foxtail Millet", "Oats", "Rye",
        "Barley", "Wheat",
    ],
    "Pulses": [
        "Lentils (Masoor)", "Chickpeas (Chana)", "Pigeon Peas (Toor / Arhar)",
        "Mung Beans (Moong)", "Black Gram (Urad)", "Beans (Rajma)",
        "Black-Eyed Peas (Lobia)", "Field Peas / Split Peas (Matar)",
    ],
    "Oil Seeds": [
        "Groundnut", "Soybean", "Rapeseed and Mustard", "Sunflower",
        "Sesame", "Safflower", "Niger", "Linseed / Flaxseed",
        "Castor", "Oil Palm", "Coconut",
    ],
    "Vegetables": [
        "Spinach", "Cabbage", "Kale", "Swiss Chard", "Microgreens",
        "Carrot", "Potato", "Sweet Potato", "Radish", "Beetroot",
        "Turnip", "Cauliflower", "Broccoli", "Brussels Sprouts",
        "Tomato", "Eggplant (Brinjal)", "Bell Pepper & Chili (Capsicum)",
        "Cucumber", "Okra (Lady's Finger)", "Green Beans", "Peas",
        "Onion", "Garlic", "Leek",
        "Pumpkin", "Bottle Gourd", "Bitter Gourd", "Zucchini",
        "Squash (Butternut, Acorn)",
    ],
}

# Flat list for quick search / editable dropdown
ALL_CROPS = [crop for crops in CROP_CATEGORIES.values() for crop in crops]

WATER_SOURCES = ["Surface Water", "Ground Water"]

CROP_STAGES = [
    "Land Preparation",
    "Sowing",
    "Vegetative",
    "Flowering & Budding",
    "Ripening & Maturation",
    "Harvesting/Harvested",
]

SEASONS = ["Kharif", "Rabi", "Winter", "Summer"]
