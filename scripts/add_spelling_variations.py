"""
Add comprehensive Hinglish spelling variations to crops.json.
Covers: vowel doubling, z/j confusion, phonetic variants, common typos,
        informal/colloquial forms, and regional spellings.
"""
import json
from pathlib import Path

DATA_FILE = Path(__file__).parent.parent / "shared" / "data" / "crops.json"

# Map: master_name → list of (en_variation, hi_text) tuples to ADD
# hi_text can be same as existing or "" to reuse the first Hindi synonym
VARIATIONS = {
    "Acid Lime": [
        ("Nimboo", "नींबू"),
        ("Nimbo", "नींबू"),
        ("Kagzi Nimboo", "कागजी नींबू"),
        ("Kagji Nimbu", "कागजी नींबू"),
        ("Khatta Nimbu", "खट्टा नींबू"),
    ],
    "Almond": [
        ("Badaam", "बादाम"),  # already exists but just in case
        ("Baadam", "बादाम"),
        ("Badam", "बादाम"),
    ],
    "Aloe Vera": [
        ("Aloevera", "एलोवेरा"),
        ("Aloe vera", "एलोवेरा"),
        ("Gwarpatha", "ग्वारपाठा"),
        ("Gwar Patha", "ग्वारपाठा"),
        ("Ghritkumari", "घृत कुमारी"),
        ("Ghrit kumari", "घृत कुमारी"),
    ],
    "Aonla": [
        ("Aamla", "आंवला"),
        ("Aanwla", "आंवला"),
        ("Awla", "आंवला"),
        ("Aawla", "आंवला"),
        ("Amla", "आंवला"),
    ],
    "Apple": [
        ("Seb", "सेब"),
        ("Saib", "सेब"),
        ("Saeb", "सेब"),
    ],
    "Apricot": [
        ("Khubaani", "खुबानी"),
        ("Khubani", "खुबानी"),
        ("Khoobani", "खुबानी"),
    ],
    "Ash Gourd Petha": [
        ("Pethaa", "पेठा"),
        ("Safed Kaddu", "सफेद कद्दू"),
        ("Safed Kaddoo", "सफेद कद्दू"),
        ("Ash gourd", "पेठा"),
    ],
    "Babool": [
        ("Babul", "बबूल"),
        ("Babool", "बबूल"),
        ("Keekar", "कीकर"),
        ("Kikkar", "कीकर"),
        ("Kikar", "कीकर"),
    ],
    "Bael": [
        ("Bail", "बेल"),
        ("Bel", "बेल"),
        ("Bael Patthar", "बेल पत्थर"),
        ("Bel Patthar", "बेल पत्थर"),
    ],
    "Bajra Napier Hybrid": [
        ("Napier grass", "नेपियर घास"),
        ("Bajra Napier grass", "बाजरा नेपियर"),
        ("Hathi Ghass", "हाथी घास"),
        ("Haathi Ghas", "हाथी घास"),
    ],
    "Banana": [
        ("Kelaa", "केला"),
        ("Kele", "केले"),
    ],
    "Barley Jau": [
        ("Jo", "जौ"),
        ("Jav", "जौ"),
        ("Jaun", "जौ"),
        ("Jow", "जौ"),
    ],
    "Barseem": [
        ("Berseem", "बरसीम"),
        ("Barsim", "बरसीम"),
        ("Bersim", "बरसीम"),
        ("Barseem", "बरसीम"),
    ],
    "Beet Root": [
        ("Chukandar", "चुकंदर"),
        ("Chukander", "चुकंदर"),
        ("Chukundar", "चुकंदर"),
        ("Beetroot", "चुकंदर"),
        ("Beet root", "चुकंदर"),
    ],
    "Bengal Gram": [
        ("Chanaa", "चना"),
        ("Channa", "चना"),
        ("Chhana", "चना"),
        ("Chole", "छोले"),
        ("Chhole", "छोले"),
        ("Chickpea", "छोले"),
        ("Chick pea", "छोले"),
    ],
    "Ber": [
        ("Bair", "बेर"),
        ("Ber", "बेर"),
        ("Bor", "बोर"),
        ("Bore", "बोर"),
    ],
    "Bhindi": [
        ("Bhindee", "भिंडी"),
        ("Bindi", "भिंडी"),
        ("Bhindii", "भिंडी"),
        ("Okra", "भिंडी"),
        ("Lady finger", "भिंडी"),
        ("Ladyfinger", "भिंडी"),
    ],
    "Bitter Gourd": [
        ("Karele", "करेला"),
        ("Karella", "करेला"),
        ("Karelaa", "करेला"),
        ("Karele", "करेले"),
    ],
    "Black Gram": [
        ("Urad dal", "उड़द दाल"),
        ("Urad daal", "उड़द दाल"),
        ("Urd", "उड़द"),
        ("Urd dal", "उड़द दाल"),
        ("Udad", "उड़द"),
        ("Maash", "माश"),
        ("Mash", "माश"),
    ],
    "Bottle Gourd": [
        ("Loki", "लौकी"),
        ("Lowki", "लौकी"),
        ("Lokee", "लौकी"),
        ("Laukee", "लौकी"),
        ("Ghia", "घिया"),
        ("Ghiyaa", "घिया"),
        ("Kaddu Lauki", "लौकी"),
    ],
    "Brinjal": [
        ("Baigan", "बैंगन"),
        ("Bengan", "बैंगन"),
        ("Baigan", "बैंगन"),
        ("Baingan", "बैंगन"),
        ("Bangan", "बैंगन"),
        ("Bhanta", "बैंगन"),
        ("Bhatta", "भट्टा"),
        ("Eggplant", "बैंगन"),
    ],
    "Broccoli": [
        ("Brokoli", "ब्रोकोली"),
        ("Broccli", "ब्रोकोली"),
        ("Hari Gobhi", "हरी गोभी"),
        ("Hari Gobi", "हरी गोभी"),
    ],
    "Cabbage": [
        ("Patta Gobi", "पत्ता गोभी"),
        ("Patta Gobhi", "पत्ता गोभी"),
        ("Band Gobhi", "बंद गोभी"),
        ("Bandgobi", "बंद गोभी"),
        ("Bandgobhi", "बंद गोभी"),
        ("Pattagobi", "पत्ता गोभी"),
    ],
    "Capsicum": [
        ("Shimla mirchi", "शिमला मिर्ची"),
        ("Shimla Mirch", "शिमला मिर्च"),
        ("Simla Mirch", "शिमला मिर्च"),
        ("Simla Mirchi", "शिमला मिर्ची"),
        ("Bell pepper", "शिमला मिर्च"),
    ],
    "Carrot": [
        ("Gaajar", "गाजर"),
        ("Gajer", "गाजर"),
        ("Gajjar", "गाजर"),
        ("Gajar", "गाजर"),
    ],
    "Castor": [
        ("Arandi", "अरंडी"),
        ("Arandee", "अरंडी"),
        ("Arendi", "अरंडी"),
        ("Erandi", "अरंडी"),
    ],
    "Cauliflower": [
        ("Phool Gobhi", "फूल गोभी"),
        ("Fool Gobi", "फूल गोभी"),
        ("Ful Gobi", "फूल गोभी"),
        ("Phoolgobi", "फूल गोभी"),
        ("Foolgobi", "फूल गोभी"),
        ("Gobi", "फूल गोभी"),
        ("Gobhi", "गोभी"),
    ],
    "Celery": [
        ("Ajwain Khurasani", "अजवायन खुरासानी"),
        ("Seldari", "सैलरी"),
    ],
    "Chillies": [
        ("Mirch", "मिर्च"),
        ("Meerchi", "मिर्ची"),
        ("Mirchee", "मिर्ची"),
        ("Mirchii", "मिर्ची"),
        ("Hari Mirch", "हरी मिर्च"),
        ("Hari Mirchi", "हरी मिर्ची"),
        ("Laal Mirch", "लाल मिर्च"),
        ("Pepper", "मिर्च"),
        ("Chilli", "मिर्च"),
        ("Chili", "मिर्च"),
    ],
    "Chrysanthemum": [
        ("Guldaudi", "गुलदाउदी"),
        ("Guldawdi", "गुलदाउदी"),
        ("Gul Daudi", "गुलदाउदी"),
    ],
    "Coconut": [
        ("Nariyal", "नारियल"),
        ("Naryal", "नारियल"),
        ("Naariyal", "नारियल"),
        ("Naaryal", "नारियल"),
    ],
    "Colocasia": [
        ("Arbi", "अरबी"),
        ("Arbee", "अरबी"),
        ("Arvi", "अरबी"),
        ("Arvee", "अरबी"),
        ("Ghuiya", "घुइयां"),
        ("Ghuiyan", "घुइयां"),
    ],
    "Coriander": [
        ("Dhania", "धनिया"),
        ("Dhaniyaa", "धनिया"),
        ("Dhaniya", "धनिया"),
        ("Dhanya", "धनिया"),
    ],
    "Cotton Kapas": [
        ("Kapaas", "कपास"),
        ("Kapas", "कपास"),
        ("Narmaa", "नरमा"),
        ("Narma", "नरमा"),
        ("Rui", "रुई"),
        ("Rooi", "रुई"),
        ("Kapah", "कपास"),
    ],
    "Cowpea Vegetable": [
        ("Lobiya", "लोबिया"),
        ("Lobia", "लोबिया"),
        ("Lobhiya", "लोबिया"),
        ("Lobhia", "लोबिया"),
        ("Rongi", "रोंगी"),
        ("Rongee", "रोंगी"),
    ],
    "Cucumber": [
        ("Khira", "खीरा"),
        ("Khiraa", "खीरा"),
        ("Kheeraa", "खीरा"),
        ("Kheere", "खीरे"),
    ],
    "Cumin": [
        ("Jira", "जीरा"),
        ("Jeeraa", "जीरा"),
        ("Zeera", "जीरा"),
        ("Zira", "जीरा"),
        ("Jeera", "जीरा"),
    ],
    "DatePalm": [
        ("Khajoor", "खजूर"),
        ("Kajur", "खजूर"),
        ("Khajur", "खजूर"),
        ("Khajuri", "खजूर"),
    ],
    "Dhaincha": [
        ("Dhainchaa", "ढैंचा"),
        ("Dhencha", "ढैंचा"),
        ("Dhenchaa", "ढैंचा"),
    ],
    "Drum Stick": [
        ("Sahjan", "सहजन"),
        ("Sahjaan", "सहजन"),
        ("Sahajan", "सहजन"),
        ("Moringa", "सहजन"),
        ("Munga", "मुंगा"),
        ("Mungaa", "मुंगा"),
        ("Drumstick", "सहजन"),
    ],
    "Eculeptous": [
        ("Eucalyptus", "यूकेलिप्टस"),
        ("Nilgiri", "यूकेलिप्टस"),
        ("Safeda", "सफेदा"),
        ("Safedaa", "सफेदा"),
    ],
    "Fennel": [
        ("Saunf", "सौंफ"),
        ("Sauf", "सौंफ"),
        ("Sonf", "सौंफ"),
        ("Sownf", "सौंफ"),
        ("Soanf", "सौंफ"),
    ],
    "Fig": [
        ("Anjir", "अंजीर"),
        ("Anjeer", "अंजीर"),
        ("Anjear", "अंजीर"),
    ],
    "FingerMillet Ragi": [
        ("Raagi", "रागी"),
        ("Mandua", "मंडुआ"),
        ("Manduaa", "मंडुआ"),
        ("Nachni", "रागी"),
        ("Nachani", "रागी"),
    ],
    "French Bean": [
        ("Faras Bean", "फरास बीन"),
        ("Faraas Bean", "फरास बीन"),
        ("Rajma Bean", "फ्रेंच बीन"),
        ("French bean", "फ्रेंच बीन"),
    ],
    "Garlic": [
        ("Lahsun", "लहसुन"),
        ("Lasun", "लहसुन"),
        ("Lasan", "लहसुन"),
        ("Lehsoon", "लहसुन"),
        ("Lahsoon", "लहसुन"),
    ],
    "Gerbera": [
        ("Jerbera", "जरबेरा"),
        ("Jarberaa", "जरबेरा"),
    ],
    "Ginger": [
        ("Adrakh", "अदरक"),
        ("Adarak", "अदरक"),
        ("Aadrak", "अदरक"),
        ("Adrak", "अदरक"),
    ],
    "Gladiolus": [
        ("Gladiolus", "ग्लैडियोलस"),
        ("Glediolas", "ग्लैडियोलस"),
    ],
    "Grape": [
        ("Angur", "अंगूर"),
        ("Angoor", "अंगूर"),
        ("Angur", "अंगूर"),
        ("Angor", "अंगूर"),
    ],
    "Green Gram": [
        ("Mung", "मूंग"),
        ("Moong dal", "मूंग दाल"),
        ("Mung dal", "मूंग दाल"),
        ("Moongh", "मूंग"),
        ("Moong daal", "मूंग दाल"),
    ],
    "Groundnut": [
        ("Mungfali", "मूंगफली"),
        ("Moongfali", "मूंगफली"),
        ("Mungphali", "मूंगफली"),
        ("Peanut", "मूंगफली"),
        ("Moongfaali", "मूंगफली"),
    ],
    "Guar": [
        ("Gwar", "ग्वार"),
        ("Guaar", "ग्वार"),
        ("Gwaar", "ग्वार"),
        ("Guar phali", "ग्वार फली"),
        ("Gwar phali", "ग्वार फली"),
        ("Cluster bean", "ग्वार"),
    ],
    "Guava": [
        ("Amrud", "अमरूद"),
        ("Amrood", "अमरूद"),
        ("Amroud", "अमरूद"),
        ("Amarood", "अमरूद"),
    ],
    "Guinea Grass": [
        ("Gini Ghas", "गिनी घास"),
        ("Gini Ghass", "गिनी घास"),
    ],
    "Hibiscus": [
        ("Gudhal", "गुड़हल"),
        ("Gurhal", "गुड़हल"),
        ("Gudahal", "गुड़हल"),
        ("Jasud", "गुड़हल"),
    ],
    "Indian Squash Tinda": [
        ("Tinda", "टिंडा"),
        ("Tindaa", "टिंडा"),
        ("Tindey", "टिंडे"),
        ("Tinde", "टिंडे"),
    ],
    "Jackfruit": [
        ("Kathal", "कटहल"),
        ("Katahal", "कटहल"),
        ("Kathhal", "कटहल"),
    ],
    "Jamun": [
        ("Jaamun", "जामुन"),
        ("Jamoon", "जामुन"),
        ("Java Plum", "जामुन"),
    ],
    "Jasmine": [
        ("Chameli", "चमेली"),
        ("Chamilee", "चमेली"),
        ("Belaa", "बेला"),
        ("Mogra", "मोगरा"),
    ],
    "Kaner": [
        ("Kaneer", "कनेर"),
        ("Kaner", "कनेर"),
    ],
    "Kiwi Fruit": [
        ("Kiwi", "कीवी"),
        ("Keewi", "कीवी"),
        ("Kiwi fruit", "कीवी"),
    ],
    "Karonda": [
        ("Karonda", "करौंदा"),
        ("Koronda", "करौंदा"),
        ("Karaunda", "करौंदा"),
        ("Karondaa", "करौंदा"),
    ],
    "Lemon": [
        ("Nimboo", "नींबू"),
        ("Nimbo", "नींबू"),
        ("Lebu", "नींबू"),
    ],
    "Lentil Masur": [
        ("Masoor", "मसूर"),
        ("Masur dal", "मसूर दाल"),
        ("Masoor dal", "मसूर दाल"),
        ("Masoor daal", "मसूर दाल"),
        ("Masur daal", "मसूर दाल"),
    ],
    "Litchi": [
        ("Lichi", "लीची"),
        ("Lychee", "लीची"),
        ("Leechee", "लीची"),
        ("Litchee", "लीची"),
    ],
    "Long Melon": [
        ("Kakdi", "ककड़ी"),
        ("Kakree", "ककड़ी"),
        ("Kakadee", "ककड़ी"),
    ],
    "Maize Makka": [
        ("Makkaa", "मक्का"),
        ("Makkai", "मक्का"),
        ("Makki", "मक्का"),
        ("Corn", "मक्का"),
        ("Bhutta", "भुट्टा"),
        ("Chhalli", "छल्ली"),
        ("Challi", "छल्ली"),
    ],
    "Mango": [
        ("Aam", "आम"),
        ("Am", "आम"),
        ("Aamb", "आम"),
    ],
    "Marigold": [
        ("Genda", "गेंदा"),
        ("Gendaa", "गेंदा"),
        ("Gainda", "गेंदा"),
        ("Gaindaa", "गेंदा"),
    ],
    "Mentha": [
        ("Menthaa", "मेंथा"),
        ("Minthaa", "मेंथा"),
    ],
    "Methi Fenugreek": [
        ("Methee", "मेथी"),
        ("Meethi", "मेथी"),
        ("Methi", "मेथी"),
        ("Kasuri Methi", "कसूरी मेथी"),
    ],
    "Mosambi": [
        ("Mosambee", "मोसंबी"),
        ("Mosambi", "मोसंबी"),
        ("Mausambi", "मौसंबी"),
        ("Mausami", "मौसंबी"),
        ("Mosami", "मोसंबी"),
        ("Sweet lime", "मोसंबी"),
    ],
    "Mint": [
        ("Pudinaa", "पुदीना"),
        ("Podina", "पुदीना"),
        ("Podeena", "पुदीना"),
    ],
    "Moth Bean": [
        ("Moth", "मोठ"),
        ("Matki", "मोठ"),
    ],
    "Mulberry": [
        ("Shahtoot", "शहतूत"),
        ("Shehtoot", "शहतूत"),
        ("Shahtut", "शहतूत"),
        ("Toot", "शहतूत"),
    ],
    "Mushroom": [
        ("Khumbi", "खुंब"),
        ("Khumbee", "खुंब"),
        ("Mashroom", "मशरूम"),
        ("Kukurmutta", "मशरूम"),
    ],
    "Musk Melon": [
        ("Kharbooja", "खरबूजा"),
        ("Kharbuja", "खरबूजा"),
        ("Kharbuza", "खरबूजा"),
        ("Kharbooza", "खरबूजा"),
    ],
    "Mustard": [
        ("Sarsoon", "सरसों"),
        ("Sarso", "सरसों"),
        ("Sarsoo", "सरसों"),
        ("Sarson", "सरसों"),
        ("Rayaa", "राया"),
        ("Raya", "राया"),
        ("Laha", "लाहा"),
    ],
    "Neem": [
        ("Neem", "नीम"),
        ("Nim", "नीम"),
    ],
    "Oats": [
        ("Jai", "जई"),
        ("Jaee", "जई"),
        ("Javee", "जई"),
    ],
    "Onion": [
        ("Pyaaj", "प्याज"),
        ("Pyaaz", "प्याज"),
        ("Piyaj", "प्याज"),
        ("Piyaz", "प्याज"),
        ("Piaz", "प्याज"),
        ("Piaj", "प्याज"),
        ("Pyaaj", "प्याज"),
        ("Pyaz", "प्याज"),
        ("Pyaj", "प्याज"),
        ("Kanda", "प्याज"),
        ("Dungri", "प्याज"),
    ],
    "Orange": [
        ("Santra", "संतरा"),
        ("Santara", "संतरा"),
        ("Santraa", "संतरा"),
        ("Maltaa", "माल्टा"),
        ("Kinnu", "किन्नू"),
        ("Kinnoo", "किन्नू"),
    ],
    "Paddy Dhan": [
        ("Dhaan", "धान"),
        ("Rice", "चावल"),
        ("Chaval", "चावल"),
        ("Chavaal", "चावल"),
        ("Jhonaa", "झोना"),
    ],
    "Palmyra": [
        ("Tad", "ताड़"),
        ("Taad", "ताड़"),
        ("Tar", "ताड़"),
    ],
    "Papaya": [
        ("Papita", "पपीता"),
        ("Papeetaa", "पपीता"),
        ("Papeeta", "पपीता"),
        ("Papitaa", "पपीता"),
    ],
    "Peach": [
        ("Aadoo", "आड़ू"),
        ("Aroo", "आड़ू"),
        ("Aadu", "आड़ू"),
        ("Aaroo", "आड़ू"),
    ],
    "Pear": [
        ("Nashpaati", "नाशपाती"),
        ("Naashpati", "नाशपाती"),
        ("Nashpatti", "नाशपाती"),
    ],
    "Pearl Millet Bajra": [
        ("Bajraa", "बाजरा"),
        ("Baajra", "बाजरा"),
        ("Bajara", "बाजरा"),
        ("Bajre", "बाजरे"),
        ("Baajraa", "बाजरा"),
    ],
    "Peas": [
        ("Mattar", "मटर"),
        ("Mutter", "मटर"),
        ("Mataar", "मटर"),
        ("Mattaar", "मटर"),
        ("Mater", "मटर"),
    ],
    "Pigeon Pea": [
        ("Arahar", "अरहर"),
        ("Arhar dal", "अरहर दाल"),
        ("Toor", "तूर"),
        ("Toor dal", "तूर दाल"),
        ("Tur dal", "तूर दाल"),
        ("Tur daal", "तूर दाल"),
    ],
    "Plum": [
        ("Aloo Bukhara", "आलू बुखारा"),
        ("Alubukhara", "आलू बुखारा"),
        ("Alu Bukhara", "आलू बुखारा"),
        ("Aaloobukhara", "आलू बुखारा"),
    ],
    "Pointed Gourd": [
        ("Parval", "परवल"),
        ("Parwaal", "परवल"),
        ("Parval", "परवल"),
        ("Patal", "परवल"),
    ],
    "Pomegranate": [
        ("Anaar", "अनार"),
        ("Anar", "अनार"),
        ("Daana", "अनार"),
    ],
    "Poplar": [
        ("Poplar", "पॉपलर"),
        ("Poplaar", "पॉपलर"),
    ],
    "Potato": [
        ("Aaloo", "आलू"),
        ("Alu", "आलू"),
        ("Aaloo", "आलू"),
        ("Alloo", "आलू"),
    ],
    "Pumpkin": [
        ("Kaddoo", "कद्दू"),
        ("Kadu", "कद्दू"),
        ("Kadoo", "कद्दू"),
        ("Sitaphal", "कद्दू"),
        ("Lal Kaddu", "कद्दू"),
    ],
    "Radish": [
        ("Muli", "मूली"),
        ("Moolee", "मूली"),
        ("Mulee", "मूली"),
    ],
    "Rajma": [
        ("Raajma", "राजमा"),
        ("Rajmaa", "राजमा"),
        ("Raajmaa", "राजमा"),
        ("Kidney bean", "राजमा"),
    ],
    "Ridge Gourd": [
        ("Tori", "तोरई"),
        ("Toree", "तोरई"),
        ("Torai", "तोरई"),
        ("Turi", "तोरई"),
        ("Turai", "तोरई"),
        ("Kali Tori", "काली तोरई"),
    ],
    "Rocket Salad": [
        ("Rocket salad", "रॉकेट सलाद"),
        ("Arugula", "रॉकेट सलाद"),
    ],
    "Rose": [
        ("Gulaab", "गुलाब"),
        ("Gulab", "गुलाब"),
    ],
    "Safed Musli": [
        ("Safed Moosli", "सफेद मूसली"),
        ("Safed Musali", "सफेद मूसली"),
    ],
    "Sagoan": [
        ("Sagwan", "सागवान"),
        ("Saagwan", "सागवान"),
        ("Sagwaan", "सागवान"),
        ("Teak", "सागवान"),
    ],
    "Sapota": [
        ("Cheeku", "चीकू"),
        ("Chikoo", "चीकू"),
        ("Chiku", "चीकू"),
        ("Chikku", "चीकू"),
        ("Sapodilla", "चीकू"),
    ],
    "Sesame": [
        ("Till", "तिल"),
        ("Teel", "तिल"),
        ("Til", "तिल"),
    ],
    "Snake Gourd": [
        ("Chichinda", "चिचिंडा"),
        ("Chichindaa", "चिचिंडा"),
        ("Chachinda", "चिचिंडा"),
    ],
    "Snap Melon": [
        ("Phoot", "फूट"),
        ("Phut", "फूट"),
        ("Kachara", "कचरा"),
        ("Kachraa", "कचरा"),
    ],
    "Sorghum Jowar": [
        ("Jwar", "ज्वार"),
        ("Jawar", "ज्वार"),
        ("Jawaar", "ज्वार"),
        ("Jowar", "ज्वार"),
        ("Chari", "चरी"),
        ("Charri", "चरी"),
    ],
    "Soyabean": [
        ("Soybean", "सोयाबीन"),
        ("Soya", "सोयाबीन"),
        ("Soyabin", "सोयाबीन"),
        ("Soy", "सोयाबीन"),
    ],
    "Spinach Palak": [
        ("Paalak", "पालक"),
        ("Palak", "पालक"),
        ("Saag", "पालक"),
    ],
    "Spine Gourd": [
        ("Kakoda", "ककोड़ा"),
        ("Kakodaa", "ककोड़ा"),
        ("Kantola", "ककोड़ा"),
    ],
    "Sponge Gourd": [
        ("Gilki", "घिया तोरई"),
        ("Gilkee", "घिया तोरई"),
        ("Ghiya Torai", "घिया तोरई"),
        ("Ghia Torai", "घिया तोरई"),
        ("Nenua", "तोरई"),
    ],
    "Strawberry": [
        ("Straberry", "स्ट्रॉबेरी"),
        ("Strawberi", "स्ट्रॉबेरी"),
    ],
    "Sudan Grass": [
        ("Sudan ghas", "सूडान घास"),
        ("Sudan ghass", "सूडान घास"),
    ],
    "Sugarcane": [
        ("Gannaa", "गन्ना"),
        ("Ganne", "गन्ने"),
        ("Ikshu", "गन्ना"),
    ],
    "Sunflower": [
        ("Surajmukhee", "सूरजमुखी"),
        ("Suraj mukhi", "सूरजमुखी"),
        ("Surajmukhi", "सूरजमुखी"),
    ],
    "Tobacco": [
        ("Tambaaku", "तंबाकू"),
        ("Tambakoo", "तंबाकू"),
        ("Tambaku", "तंबाकू"),
        ("Tamaku", "तंबाकू"),
    ],
    "Tomato": [
        ("Tamaatar", "टमाटर"),
        ("Tamater", "टमाटर"),
        ("Tamatar", "टमाटर"),
        ("Tamatar", "टमाटर"),
    ],
    "Toria": [
        ("Toriya", "तोरिया"),
        ("Toriyaa", "तोरिया"),
    ],
    "Tulsi": [
        ("Tulasi", "तुलसी"),
        ("Tulsee", "तुलसी"),
        ("Basil", "तुलसी"),
    ],
    "Turmeric": [
        ("Haaldi", "हल्दी"),
        ("Haldee", "हल्दी"),
        ("Haldi", "हल्दी"),
    ],
    "Turnip": [
        ("Shalgam", "शलगम"),
        ("Shaljam", "शलगम"),
        ("Salgam", "शलगम"),
    ],
    "Watermelon": [
        ("Tarbooj", "तरबूज"),
        ("Tarbuz", "तरबूज"),
        ("Tarbooz", "तरबूज"),
        ("Tarbooja", "तरबूजा"),
    ],
    "Wheat": [
        ("Gehun", "गेहूं"),
        ("Gehoo", "गेहूं"),
        ("Gehoon", "गेहूं"),
        ("Gehu", "गेहूं"),
        ("Kanak", "कनक"),
        ("Kanaq", "कनक"),
    ],
    "Yard Long Bean": [
        ("Lobiya Phali", "लोबिया फली"),
        ("Lobia Phali", "लोबिया फली"),
        ("Barbati", "लोबिया फली"),
        ("Borboti", "लोबिया फली"),
    ],
    "Cashew Nut": [
        ("Kaju", "काजू"),
        ("Kaaju", "काजू"),
        ("Kajoo", "काजू"),
    ],
    "Citrus": [
        ("Citrus", "सिट्रस"),
        ("Nimbu Vargiya", "नींबू वर्गीय"),
    ],
    "Dragon Fruit": [
        ("Dragonfruit", "ड्रैगन फ्रूट"),
        ("Pitaya", "ड्रैगन फ्रूट"),
        ("Kamalam", "कमलम"),
    ],
}


def main():
    with open(DATA_FILE, "r") as f:
        data = json.load(f)

    added_count = 0
    for crop in data["crops"]:
        master = crop["master_name"]
        if master not in VARIATIONS:
            continue

        # Get existing en values (lowercase for dedup)
        existing_en = {s["en"].lower() for s in crop["synonyms"]}

        for en_var, hi_var in VARIATIONS[master]:
            if en_var.lower() not in existing_en:
                crop["synonyms"].append({"en": en_var, "hi": hi_var})
                existing_en.add(en_var.lower())
                added_count += 1

    # Save
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    total = sum(len(c["synonyms"]) for c in data["crops"])
    print(f"Added {added_count} new variations")
    print(f"Total synonyms now: {total}")
    print(f"Avg per crop: {total/len(data['crops']):.1f}")


if __name__ == "__main__":
    main()
