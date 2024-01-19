import pygame
from .npc import NPC

first_names = [
    "Jimmy", "John", "Paddy", "Rob", "Jeff", "Mikey", "Mike",
    "William", "Eldis", "David", "Will", "Richard", "Sue", "Jose", "Jake",
    "Thomas", "Sarah", "Charlie", "Karen", "Christopher", "Nance", "Daniel", "Lisa",
    "Matthew", "Margaret", "Anthony", "Betty", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
    "Kenneth", "Dorothy", "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa",
    "Edward", "Deborah", "Ronald", "Stephanie", "Timmy", "Rebecca", "Jason", "Sharon",
    "Jeffrey", "Laura", "Ryan", "Cynthia", "Jacob", "Kathleen", "Gary", "Amy",
    "Nicholas", "Shirley", "Eric", "Angela", "Jonathan", "Helen", "Stephen", "Anna",
    "Larry", "Brenda", "Justin", "Pamela", "Scott", "Nicole", "Brandon", "Samantha",
    "Benjamin", "Katherine", "Samuel", "Emma", "Frank", "Ruth", "Gregory", "Olivia",
    "Raymond", "Ava", "Alexander", "Sophia", "Patrick", "Isabella", "Jack", "Mia",
    "Dennis", "Charlotte", "Jerry", "Harper", "Tyler", "Grace", "Aaron", "Chloe"
]

last_names = [
    "Smith", "Johnson", "Williams", "Brown", "Jones",
    "Miller", "Davis", "Garcia", "Rodriguez", "Wilson",
    "Martinez", "Anderson", "Taylor", "Thomas", "Hernandez",
    "Moore", "Martin", "Jackson", "Thompson", "White",
    "Lopez", "Lee", "Gonzalez", "Harris", "Clark",
    "Lewis", "Robinson", "Walker", "Perez", "Hall",
    "Young", "Allen", "Sanchez", "Wright", "King",
    "Scott", "Green", "Baker", "Nelson",
    "Hill", "Ramirez", "Campbell", "Mitchell", "Roberts",
    "Carter", "Phillips", "Evans", "Turner", "Torres",
    "Parker", "Collins", "Edwards", "Stewart", "Flores",
    "Morris", "Nguyen", "Murphy", "Rivera", "Cook",
    "Rogers", "Morgan", "Peterson", "Cooper", "Reed",
    "Bailey", "Bell", "Gomez", "Kelly", "Howard",
    "Ward", "Cox", "Diaz", "Richardson", "Wood",
    "Watson", "Brooks", "Bennett", "Gray", "James",
    "Reyes", "Cruz", "Hughes", "Price", "Myers",
    "Long", "Foster", "Sanders", "Ross", "Morales",
    "Powell", "Sullivan", "Russell", "Ortiz", "Jenkins",
    "Gutierrez", "Perry", "Butler", "Barnes", "Fisher"
]

hobbies = [
    "Reading", "Writing", "Drawing", "Painting", "Photography",
    "Gardening", "Underwater Basket Weaving", "Baking", "Knitting", "Crocheting",
    "Sewing", "Woodworking", "Pottery", "Ceramics", "Jewelry Making",
    "Scrapbooking", "Singing", "Dancing", "Acting", "Snail Climbing",
    "Stand-up Comedy", "Magic", "Juggling", "Yoga", "Pilates",
    "Meditation", "Fitness Training", "Running", "Hiking",
    "Camping", "Backpacking", "Rock Collecting", "Kayaking",
    "Canoeing", "Surfing", "Snowboarding", "Skiing", "Skateboarding",
    "Cycling", "Competitive Napping", "Scootering", "Roller Skating",
    "Ice Skating", "Horseback Riding", "Horseback Martial Arts", "Archery", "Frog Fencing",
    "Boxing", "Martial Arts", "Yoga", "Plant Whispering", "Golfing",
    "Tennis", "Badminton", "Table Tennis", "Bowling",
    "Billiards", "Darts", "Chess", "Board Games", "Extreme Ironing",
    "Cosplay", "Non-Fiction LARPing", "Model Building",
    "Drone Sitting", "RC Car Racing", "Aquascaping", "Fishkeeping",
    "Birdwatching", "Stargazing", "Meteorology", "Geocaching",
    "Extreme Metal Detecting", "Treasure Hunting", "Traveling", "Language Learning",
    "History", "Genealogy", "Philosophy", "Astrology",
    "Tarot Reading", "Numerology", "Blogging", "Vlogging",
    "Podcasting", "Listening to Music", "Amateur Cloud Shaping", "Theater Going",
    "Attending Concerts", "Visiting Museums", "Backyard Dam Construction",
    "Wine Tasting", "Beer Brewing", "Whiskey Tasting", "Coffee Roasting",
    "Tea Brewing", "Soap Making", "Candle Making", "Perfumery", "Fishing", "Self Dentistry",
    "Competative Duck Herding", "Balloon Animal Taxidermy", "Synchronized Solo Dancing"
]

class Miner(NPC):
    def __init__(self):
        super().__init__() #Base Class Attributes
        self.sprite = "space/assets/img/objects/miner.png"

class Foreman(NPC):
    def __init__(self):
        super().__init__() #Base Class Attributes
        self.sprite = "space/assets/img/objects/foreman.png"

class Politician(NPC):
    def __init__(self):
        super().__init__() #Base Class Attributes
        self.sprite = "space/assets/img/objects/politician.png"

class Security(NPC):
    def __init__(self):
        super().__init__() #Base Class Attributes
        self.sprite = "space/assets/img/objects/security.png"
