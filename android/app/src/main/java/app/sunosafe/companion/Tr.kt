package app.sunosafe.companion

import android.content.Context

/**
 * On-screen text of the main screen in the five SunoSafe languages, following the
 * language chosen in the app (the same setting as the spoken warnings).
 * Order in every entry: English, Hindi, Malayalam, Kannada, Tamil.
 * Machine-assisted translations, not yet reviewed by native speakers.
 */
object Tr {
    private val ORDER = listOf("en", "hi", "ml", "kn", "ta")

    private val S: Map<String, List<String>> = mapOf(
        "subtitle" to listOf("Scam guardian", "धोखाधड़ी से रक्षक", "തട്ടിപ്പ് സംരക്ഷകൻ", "ವಂಚನೆ ರಕ್ಷಕ", "மோசடிக் காவலர்"),
        "protecting" to listOf("Protecting you", "आपकी सुरक्षा चालू है", "നിങ്ങളെ സംരക്ഷിക്കുന്നു", "ನಿಮ್ಮನ್ನು ರಕ್ಷಿಸುತ್ತಿದೆ", "உங்களைப் பாதுகாக்கிறது"),
        "setupNeeded" to listOf("Setup needed", "सेटअप बाकी है", "സജ്ജീകരണം ആവശ്യമാണ്", "ಸೆಟಪ್ ಬಾಕಿ ಇದೆ", "அமைப்பு தேவை"),
        "statusOn" to listOf(
            "SunoSafe will warn you aloud when a message or caller looks like a scam.",
            "जब कोई संदेश या कॉल करने वाला धोखाधड़ी जैसा लगेगा, SunoSafe आपको बोलकर चेतावनी देगा।",
            "ഒരു സന്ദേശമോ വിളിക്കുന്നയാളോ തട്ടിപ്പ് പോലെ തോന്നിയാൽ SunoSafe ഉറക്കെ മുന്നറിയിപ്പ് നൽകും.",
            "ಸಂದೇಶ ಅಥವಾ ಕರೆ ಮಾಡುವವರು ವಂಚನೆಯಂತೆ ಕಂಡರೆ SunoSafe ಜೋರಾಗಿ ಎಚ್ಚರಿಸುತ್ತದೆ.",
            "ஒரு செய்தி அல்லது அழைப்பவர் மோசடி போல் தெரிந்தால் SunoSafe சத்தமாக எச்சரிக்கும்."),
        "statusOff" to listOf(
            "Finish the steps below so SunoSafe can warn you without being asked.",
            "नीचे के चरण पूरे करें, ताकि SunoSafe बिना पूछे चेतावनी दे सके।",
            "താഴെയുള്ള ഘട്ടങ്ങൾ പൂർത്തിയാക്കുക, അപ്പോൾ ചോദിക്കാതെ തന്നെ SunoSafe മുന്നറിയിപ്പ് നൽകും.",
            "ಕೆಳಗಿನ ಹಂತಗಳನ್ನು ಮುಗಿಸಿ, ಆಗ ಕೇಳದೆಯೇ SunoSafe ಎಚ್ಚರಿಸುತ್ತದೆ.",
            "கீழே உள்ள படிகளை முடிக்கவும்; அப்போது கேட்காமலேயே SunoSafe எச்சரிக்கும்."),
        "chkNotif" to listOf("Notification access", "सूचना पढ़ने की अनुमति", "അറിയിപ്പ് ആക്സസ്", "ಅಧಿಸೂಚನೆ ಪ್ರವೇಶ", "அறிவிப்பு அணுகல்"),
        "chkWarn" to listOf("Allowed to show warnings", "चेतावनी दिखाने की अनुमति", "മുന്നറിയിപ്പ് കാണിക്കാൻ അനുമതി", "ಎಚ್ಚರಿಕೆ ತೋರಿಸಲು ಅನುಮತಿ", "எச்சரிக்கை காட்ட அனுமதி"),
        "chkPaired" to listOf("Connected to your SunoSafe", "आपके SunoSafe से जुड़ा", "നിങ്ങളുടെ SunoSafe-മായി ബന്ധിപ്പിച്ചു", "ನಿಮ್ಮ SunoSafe ಗೆ ಸಂಪರ್ಕಿತ", "உங்கள் SunoSafe-உடன் இணைக்கப்பட்டது"),
        "chkCalls" to listOf("Checking incoming callers", "आने वाली कॉल की जाँच", "വരുന്ന കോളുകൾ പരിശോധിക്കുന്നു", "ಒಳಬರುವ ಕರೆಗಳ ಪರಿಶೀಲನೆ", "வரும் அழைப்புகளைச் சரிபார்த்தல்"),
        "chkScreen" to listOf("Checking messages on screen (WhatsApp, SMS)", "स्क्रीन पर संदेशों की जाँच (WhatsApp, SMS)", "സ്ക്രീനിലെ സന്ദേശങ്ങൾ പരിശോധിക്കുന്നു (WhatsApp, SMS)", "ಪರದೆಯ ಮೇಲಿನ ಸಂದೇಶ ಪರಿಶೀಲನೆ (WhatsApp, SMS)", "திரையில் உள்ள செய்திகளைச் சரிபார்த்தல் (WhatsApp, SMS)"),
        "chkSms" to listOf("Reading new SMS and the SMS inbox", "नए SMS और SMS इनबॉक्स पढ़ना", "പുതിയ SMS-ഉം SMS ഇൻബോക്സും വായിക്കുന്നു", "ಹೊಸ SMS ಮತ್ತು SMS ಇನ್‌ಬಾಕ್ಸ್ ಓದುವುದು", "புதிய SMS மற்றும் SMS இன்பாக்ஸைப் படித்தல்"),
        "chkRunning" to listOf("Protection running in the background", "पृष्ठभूमि में सुरक्षा चालू", "പശ്ചാത്തലത്തിൽ സംരക്ഷണം പ്രവർത്തിക്കുന്നു", "ಹಿನ್ನೆಲೆಯಲ್ಲಿ ರಕ್ಷಣೆ ಚಾಲೂ", "பின்னணியில் பாதுகாப்பு இயங்குகிறது"),
        "callHistory" to listOf("Call history", "कॉल इतिहास", "കോൾ ചരിത്രം", "ಕರೆ ಇತಿಹಾಸ", "அழைப்பு வரலாறு"),
        "threatLogs" to listOf("Threat logs", "खतरे का रिकॉर्ड", "ഭീഷണി രേഖകൾ", "ಅಪಾಯದ ದಾಖಲೆಗಳು", "அச்சுறுத்தல் பதிவுகள்"),
        "dashboard" to listOf("SIEM dashboard", "SIEM डैशबोर्ड", "SIEM ഡാഷ്ബോർഡ്", "SIEM ಡ್ಯಾಶ್‌ಬೋರ್ಡ್", "SIEM டாஷ்போர்டு"),
        "checkTitle" to listOf("Check a message", "संदेश जाँचें", "സന്ദേശം പരിശോധിക്കുക", "ಸಂದೇಶ ಪರಿಶೀಲಿಸಿ", "செய்தியைச் சரிபார்"),
        "checkDesc" to listOf(
            "Press and hold a message in WhatsApp or Messages → Share → SunoSafe. Or copy it, come back and tap the green button.",
            "WhatsApp या Messages में संदेश दबाकर रखें → Share → SunoSafe। या उसे कॉपी करें, यहाँ लौटें और हरा बटन दबाएँ।",
            "WhatsApp-ലോ Messages-ലോ സന്ദേശം അമർത്തിപ്പിടിക്കുക → Share → SunoSafe. അല്ലെങ്കിൽ കോപ്പി ചെയ്ത് ഇവിടെ വന്ന് പച്ച ബട്ടൺ തൊടുക.",
            "WhatsApp ಅಥವಾ Messages ನಲ್ಲಿ ಸಂದೇಶವನ್ನು ಒತ್ತಿ ಹಿಡಿಯಿರಿ → Share → SunoSafe. ಅಥವಾ ಕಾಪಿ ಮಾಡಿ, ಇಲ್ಲಿಗೆ ಬಂದು ಹಸಿರು ಬಟನ್ ಒತ್ತಿ.",
            "WhatsApp அல்லது Messages-இல் செய்தியை அழுத்திப் பிடி → Share → SunoSafe. அல்லது நகலெடுத்து, இங்கே வந்து பச்சை பொத்தானைத் தொடவும்."),
        "checkCopied" to listOf("Check the message I copied", "मेरा कॉपी किया संदेश जाँचें", "ഞാൻ കോപ്പി ചെയ്ത സന്ദേശം പരിശോധിക്കുക", "ನಾನು ಕಾಪಿ ಮಾಡಿದ ಸಂದೇಶ ಪರಿಶೀಲಿಸಿ", "நான் நகலெடுத்த செய்தியைச் சரிபார்"),
        "openWa" to listOf("Open WhatsApp", "WhatsApp खोलें", "WhatsApp തുറക്കുക", "WhatsApp ತೆರೆಯಿರಿ", "WhatsApp-ஐத் திற"),
        "openSms" to listOf("Open Messages", "Messages खोलें", "Messages തുറക്കുക", "Messages ತೆರೆಯಿರಿ", "Messages-ஐத் திற"),
        "hearTitle" to listOf("Hear SunoSafe", "SunoSafe को सुनें", "SunoSafe കേൾക്കുക", "SunoSafe ಕೇಳಿ", "SunoSafe-ஐக் கேள்"),
        "hearDesc" to listOf(
            "Talk to the SunoSafe voice agent (Agora Conversational AI with a Murf Falcon voice).",
            "SunoSafe वॉइस एजेंट से बात करें (Agora Conversational AI, Murf Falcon आवाज़)।",
            "SunoSafe വോയ്സ് ഏജന്റിനോട് സംസാരിക്കുക (Agora Conversational AI, Murf Falcon ശബ്ദം).",
            "SunoSafe ಧ್ವನಿ ಏಜೆಂಟ್ ಜೊತೆ ಮಾತನಾಡಿ (Agora Conversational AI, Murf Falcon ಧ್ವನಿ).",
            "SunoSafe குரல் முகவருடன் பேசுங்கள் (Agora Conversational AI, Murf Falcon குரல்)."),
        "talkLatest" to listOf("Talk about my latest warning", "मेरी आख़िरी चेतावनी के बारे में बात करें", "എന്റെ അവസാന മുന്നറിയിപ്പിനെക്കുറിച്ച് സംസാരിക്കുക", "ನನ್ನ ಕೊನೆಯ ಎಚ್ಚರಿಕೆಯ ಬಗ್ಗೆ ಮಾತನಾಡಿ", "என் கடைசி எச்சரிக்கை பற்றிப் பேசு"),
        "drill" to listOf("Practise: scam call drill", "अभ्यास: धोखाधड़ी कॉल से बचना", "പരിശീലനം: തട്ടിപ്പ് കോൾ", "ಅಭ್ಯಾಸ: ವಂಚನೆ ಕರೆ", "பயிற்சி: மோசடி அழைப்பு"),
        "incidents" to listOf("Open incidents and evidence", "घटनाएँ और सबूत खोलें", "സംഭവങ്ങളും തെളിവുകളും തുറക്കുക", "ಘಟನೆಗಳು ಮತ್ತು ಸಾಕ್ಷ್ಯ ತೆರೆಯಿರಿ", "சம்பவங்களும் சான்றுகளும் திற"),
        "setupTitle" to listOf("Set up", "सेटअप", "സജ്ജീകരണം", "ಸೆಟಪ್", "அமைப்பு"),
        "step1" to listOf("1.  Turn on notification access", "1.  सूचना पढ़ने की अनुमति चालू करें", "1.  അറിയിപ്പ് ആക്സസ് ഓണാക്കുക", "1.  ಅಧಿಸೂಚನೆ ಪ್ರವೇಶ ಆನ್ ಮಾಡಿ", "1.  அறிவிப்பு அணுகலை இயக்கு"),
        "step2" to listOf("2.  Allow SunoSafe to show warnings", "2.  SunoSafe को चेतावनी दिखाने दें", "2.  മുന്നറിയിപ്പ് കാണിക്കാൻ SunoSafe-നെ അനുവദിക്കുക", "2.  ಎಚ್ಚರಿಕೆ ತೋರಿಸಲು SunoSafe ಗೆ ಅನುಮತಿಸಿ", "2.  எச்சரிக்கை காட்ட SunoSafe-ஐ அனுமதி"),
        "step3" to listOf(
            "3.  Connect: open your SunoSafe web app on this phone → Settings → \"Connect Android app\".",
            "3.  जोड़ें: इस फ़ोन पर अपना SunoSafe वेब ऐप खोलें → सेटिंग्स → \"Android ऐप जोड़ें\"।",
            "3.  ബന്ധിപ്പിക്കുക: ഈ ഫോണിൽ SunoSafe വെബ് ആപ്പ് തുറക്കുക → ക്രമീകരണങ്ങൾ → \"Android ആപ്പ് ബന്ധിപ്പിക്കുക\".",
            "3.  ಸಂಪರ್ಕ: ಈ ಫೋನ್‌ನಲ್ಲಿ SunoSafe ವೆಬ್ ಆ್ಯಪ್ ತೆರೆಯಿರಿ → ಸೆಟ್ಟಿಂಗ್‌ಗಳು → \"Android ಆ್ಯಪ್ ಸಂಪರ್ಕಿಸಿ\".",
            "3.  இணை: இந்தத் தொலைபேசியில் SunoSafe வலை செயலியைத் திற → அமைப்புகள் → \"Android செயலியை இணை\"."),
        "step4" to listOf("4.  Let SunoSafe check unknown callers", "4.  SunoSafe को अनजान कॉल जाँचने दें", "4.  അപരിചിത കോളുകൾ പരിശോധിക്കാൻ SunoSafe-നെ അനുവദിക്കുക", "4.  ಅಪರಿಚಿತ ಕರೆಗಳನ್ನು ಪರಿಶೀಲಿಸಲು SunoSafe ಗೆ ಅನುಮತಿಸಿ", "4.  தெரியாத அழைப்புகளைச் சரிபார்க்க SunoSafe-ஐ அனுமதி"),
        "step5" to listOf("5.  Check messages I open in WhatsApp / SMS", "5.  WhatsApp / SMS में खोले गए संदेश जाँचें", "5.  WhatsApp / SMS-ൽ ഞാൻ തുറക്കുന്ന സന്ദേശങ്ങൾ പരിശോധിക്കുക", "5.  WhatsApp / SMS ನಲ್ಲಿ ನಾನು ತೆರೆಯುವ ಸಂದೇಶ ಪರಿಶೀಲಿಸಿ", "5.  WhatsApp / SMS-இல் நான் திறக்கும் செய்திகளைச் சரிபார்"),
        "step6" to listOf("6.  Read my SMS (new + inbox)", "6.  मेरे SMS पढ़ें (नए + इनबॉक्स)", "6.  എന്റെ SMS വായിക്കുക (പുതിയത് + ഇൻബോക്സ്)", "6.  ನನ್ನ SMS ಓದಿ (ಹೊಸ + ಇನ್‌ಬಾಕ್ಸ್)", "6.  என் SMS-ஐப் படி (புதியவை + இன்பாக்ஸ்)"),
        "battery" to listOf("Keep SunoSafe running (battery)", "SunoSafe चालू रखें (बैटरी)", "SunoSafe പ്രവർത്തിപ്പിച്ച് നിർത്തുക (ബാറ്ററി)", "SunoSafe ಚಾಲೂ ಇರಿಸಿ (ಬ್ಯಾಟರಿ)", "SunoSafe-ஐ இயங்க வை (பேட்டரி)"),
        "controls" to listOf("Controls", "नियंत्रण", "നിയന്ത്രണങ്ങൾ", "ನಿಯಂತ್ರಣಗಳು", "கட்டுப்பாடுகள்"),
        "watchScam" to listOf("Watch for scam messages", "धोखाधड़ी संदेशों पर नज़र रखें", "തട്ടിപ്പ് സന്ദേശങ്ങൾ നിരീക്ഷിക്കുക", "ವಂಚನೆ ಸಂದೇಶಗಳ ಮೇಲೆ ಕಣ್ಣಿಡಿ", "மோசடிச் செய்திகளைக் கவனி"),
        "speak" to listOf("Speak warnings aloud", "चेतावनी बोलकर सुनाएँ", "മുന്നറിയിപ്പ് ഉറക്കെ പറയുക", "ಎಚ್ಚರಿಕೆಯನ್ನು ಜೋರಾಗಿ ಹೇಳು", "எச்சரிக்கையைச் சத்தமாகச் சொல்"),
        "language" to listOf("Language (screen and warnings)", "भाषा (स्क्रीन और चेतावनी)", "ഭാഷ (സ്ക്രീനും മുന്നറിയിപ്പും)", "ಭಾಷೆ (ಪರದೆ ಮತ್ತು ಎಚ್ಚರಿಕೆ)", "மொழி (திரை மற்றும் எச்சரிக்கை)"),
        "appsToWatch" to listOf("Apps to watch", "किन ऐप पर नज़र रखें", "നിരീക്ഷിക്കേണ്ട ആപ്പുകൾ", "ಗಮನಿಸಬೇಕಾದ ಆ್ಯಪ್‌ಗಳು", "கவனிக்க வேண்டிய செயலிகள்"),
        "watchApp" to listOf("Watch {app}", "{app} पर नज़र रखें", "{app} നിരീക്ഷിക്കുക", "{app} ಗಮನಿಸಿ", "{app}-ஐக் கவனி"),
        "practice" to listOf("Try a practice warning", "अभ्यास चेतावनी आज़माएँ", "ഒരു പരിശീലന മുന്നറിയിപ്പ് പരീക്ഷിക്കുക", "ಅಭ್ಯಾಸ ಎಚ್ಚರಿಕೆ ಪ್ರಯತ್ನಿಸಿ", "பயிற்சி எச்சரிக்கையை முயற்சி செய்"),
        "activity" to listOf("Activity", "गतिविधि", "പ്രവർത്തനം", "ಚಟುವಟಿಕೆ", "செயல்பாடு"),
        "privacyTitle" to listOf("What SunoSafe reads and sends", "SunoSafe क्या पढ़ता और भेजता है", "SunoSafe എന്ത് വായിക്കുന്നു, എന്ത് അയയ്ക്കുന്നു", "SunoSafe ಏನು ಓದುತ್ತದೆ, ಏನು ಕಳುಹಿಸುತ್ತದೆ", "SunoSafe எதைப் படிக்கிறது, எதை அனுப்புகிறது"),
        "privacy" to listOf(
            "• What it looks at: notifications from the apps switched on above, new SMS, and, only if you switch on screen checking, messages shown on screen in WhatsApp and Messages. Never your photos or contacts.\n" +
                "• A message is sent for checking only if it has a link or wording often used in scams. Ordinary messages never leave this phone.\n" +
                "• For callers, SunoSafe sees only the number of callers not in your contacts. It never hears calls and never blocks them.\n" +
                "• Stored evidence masks phone numbers, card numbers and codes.\n" +
                "• Turn anything off here, or remove access in Android settings, at any time.",
            "• यह क्या देखता है: ऊपर चालू किए गए ऐप की सूचनाएँ, नए SMS, और सिर्फ़ अगर आप स्क्रीन जाँच चालू करें, तो WhatsApp और Messages में स्क्रीन पर दिखे संदेश। आपकी फ़ोटो या संपर्क कभी नहीं।\n" +
                "• कोई संदेश जाँच के लिए तभी भेजा जाता है जब उसमें लिंक हो या धोखाधड़ी में अक्सर इस्तेमाल होने वाले शब्द हों। आम संदेश इस फ़ोन से बाहर नहीं जाते।\n" +
                "• कॉल के लिए SunoSafe सिर्फ़ उन नंबरों को देखता है जो आपके संपर्कों में नहीं हैं। यह कॉल कभी नहीं सुनता और उन्हें ब्लॉक नहीं करता।\n" +
                "• सहेजे गए सबूत में फ़ोन नंबर, कार्ड नंबर और कोड छिपा दिए जाते हैं।\n" +
                "• यहाँ से कुछ भी बंद करें, या Android सेटिंग्स में अनुमति कभी भी हटा दें।",
            "• ഇത് നോക്കുന്നത്: മുകളിൽ ഓണാക്കിയ ആപ്പുകളിലെ അറിയിപ്പുകൾ, പുതിയ SMS, കൂടാതെ സ്ക്രീൻ പരിശോധന ഓണാക്കിയാൽ മാത്രം, WhatsApp-ലും Messages-ലും സ്ക്രീനിൽ കാണുന്ന സന്ദേശങ്ങൾ. നിങ്ങളുടെ ഫോട്ടോകളോ കോൺടാക്റ്റുകളോ ഒരിക്കലും ഇല്ല.\n" +
                "• ലിങ്കോ തട്ടിപ്പുകളിൽ സാധാരണ കാണുന്ന വാക്കുകളോ ഉണ്ടെങ്കിൽ മാത്രമേ ഒരു സന്ദേശം പരിശോധനയ്ക്ക് അയയ്ക്കൂ. സാധാരണ സന്ദേശങ്ങൾ ഈ ഫോണിൽ നിന്ന് പുറത്തുപോകില്ല.\n" +
                "• കോളുകളിൽ, നിങ്ങളുടെ കോൺടാക്റ്റുകളിൽ ഇല്ലാത്തവരുടെ നമ്പർ മാത്രമേ SunoSafe കാണൂ. ഇത് കോളുകൾ ഒരിക്കലും കേൾക്കുകയോ ബ്ലോക്ക് ചെയ്യുകയോ ഇല്ല.\n" +
                "• സൂക്ഷിക്കുന്ന തെളിവുകളിൽ ഫോൺ നമ്പറുകൾ, കാർഡ് നമ്പറുകൾ, കോഡുകൾ എന്നിവ മറയ്ക്കുന്നു.\n" +
                "• ഇവിടെ നിന്ന് എന്തും ഓഫാക്കാം, അല്ലെങ്കിൽ Android ക്രമീകരണങ്ങളിൽ എപ്പോൾ വേണമെങ്കിലും അനുമതി നീക്കാം.",
            "• ಇದು ಏನನ್ನು ನೋಡುತ್ತದೆ: ಮೇಲೆ ಆನ್ ಮಾಡಿದ ಆ್ಯಪ್‌ಗಳ ಅಧಿಸೂಚನೆಗಳು, ಹೊಸ SMS, ಮತ್ತು ನೀವು ಪರದೆ ಪರಿಶೀಲನೆ ಆನ್ ಮಾಡಿದರೆ ಮಾತ್ರ, WhatsApp ಮತ್ತು Messages ನಲ್ಲಿ ಪರದೆಯ ಮೇಲೆ ಕಾಣುವ ಸಂದೇಶಗಳು. ನಿಮ್ಮ ಫೋಟೋಗಳು ಅಥವಾ ಸಂಪರ್ಕಗಳನ್ನು ಎಂದಿಗೂ ಇಲ್ಲ.\n" +
                "• ಲಿಂಕ್ ಅಥವಾ ವಂಚನೆಗಳಲ್ಲಿ ಹೆಚ್ಚಾಗಿ ಬಳಸುವ ಪದಗಳಿದ್ದರೆ ಮಾತ್ರ ಸಂದೇಶವನ್ನು ಪರಿಶೀಲನೆಗೆ ಕಳುಹಿಸಲಾಗುತ್ತದೆ. ಸಾಮಾನ್ಯ ಸಂದೇಶಗಳು ಈ ಫೋನ್‌ನಿಂದ ಹೊರಗೆ ಹೋಗುವುದಿಲ್ಲ.\n" +
                "• ಕರೆಗಳಿಗೆ, ನಿಮ್ಮ ಸಂಪರ್ಕಗಳಲ್ಲಿ ಇಲ್ಲದವರ ಸಂಖ್ಯೆಯನ್ನು ಮಾತ್ರ SunoSafe ನೋಡುತ್ತದೆ. ಇದು ಕರೆಗಳನ್ನು ಎಂದಿಗೂ ಕೇಳುವುದಿಲ್ಲ, ಬ್ಲಾಕ್ ಮಾಡುವುದಿಲ್ಲ.\n" +
                "• ಉಳಿಸಿದ ಸಾಕ್ಷ್ಯದಲ್ಲಿ ಫೋನ್ ಸಂಖ್ಯೆ, ಕಾರ್ಡ್ ಸಂಖ್ಯೆ ಮತ್ತು ಕೋಡ್‌ಗಳನ್ನು ಮರೆಮಾಡಲಾಗುತ್ತದೆ.\n" +
                "• ಇಲ್ಲಿಂದ ಯಾವುದನ್ನಾದರೂ ಆಫ್ ಮಾಡಿ, ಅಥವಾ Android ಸೆಟ್ಟಿಂಗ್‌ಗಳಲ್ಲಿ ಯಾವಾಗ ಬೇಕಾದರೂ ಅನುಮತಿ ತೆಗೆದುಹಾಕಿ.",
            "• இது பார்ப்பவை: மேலே இயக்கிய செயலிகளின் அறிவிப்புகள், புதிய SMS, மேலும் திரைச் சரிபார்ப்பை இயக்கினால் மட்டும், WhatsApp, Messages-இல் திரையில் தெரியும் செய்திகள். உங்கள் புகைப்படங்களோ தொடர்புகளோ ஒருபோதும் இல்லை.\n" +
                "• இணைப்பு அல்லது மோசடிகளில் அடிக்கடி வரும் சொற்கள் இருந்தால் மட்டுமே ஒரு செய்தி சரிபார்ப்புக்கு அனுப்பப்படும். சாதாரண செய்திகள் இந்தத் தொலைபேசியை விட்டு வெளியேறாது.\n" +
                "• அழைப்புகளில், உங்கள் தொடர்புகளில் இல்லாதவர்களின் எண்ணை மட்டுமே SunoSafe பார்க்கும். இது அழைப்புகளை ஒருபோதும் கேட்காது, தடுக்காது.\n" +
                "• சேமிக்கப்படும் சான்றுகளில் தொலைபேசி எண்கள், அட்டை எண்கள், குறியீடுகள் மறைக்கப்படும்.\n" +
                "• இங்கிருந்து எதையும் அணைக்கலாம், அல்லது Android அமைப்புகளில் எப்போது வேண்டுமானாலும் அனுமதியை நீக்கலாம்."),
    )

    /** Text for [key] in the chosen language; English if a key or language is missing. */
    fun t(c: Context, key: String, vararg vars: Pair<String, String>): String {
        val entry = S[key] ?: return key
        val i = ORDER.indexOf(Prefs.lang(c)).coerceAtLeast(0)
        var text = entry.getOrNull(i) ?: entry[0]
        vars.forEach { (k, v) -> text = text.replace("{$k}", v) }
        return text
    }

    /** Every key has all five languages (checked by a unit test). */
    fun complete(): Boolean = S.values.all { it.size == ORDER.size && it.none(String::isBlank) }
}
