'use client';

/**
 * On-screen text for the main screens in the five SunoSafe languages.
 * Every entry carries all five languages, so a missing translation is a type error.
 * Translations are machine-assisted and not yet reviewed by native speakers.
 * Text that comes from the backend (verdict reasons, link findings) stays in English for now.
 */
import { createContext, useCallback, useContext } from 'react';
import type { Lang } from './api';

type Entry = Record<Lang, string>;

const S = {
  // ---- navigation and header
  'nav.home': { en: 'Home', hi: 'होम', ml: 'ഹോം', kn: 'ಮುಖಪುಟ', ta: 'முகப்பு' },
  'nav.activity': { en: 'Activity', hi: 'गतिविधि', ml: 'പ്രവർത്തനം', kn: 'ಚಟುವಟಿಕೆ', ta: 'செயல்பாடு' },
  'nav.reports': { en: 'Reports', hi: 'रिपोर्ट', ml: 'റിപ്പോർട്ടുകൾ', kn: 'ವರದಿಗಳು', ta: 'அறிக்கைகள்' },
  'nav.profile': { en: 'Profile', hi: 'प्रोफ़ाइल', ml: 'പ്രൊഫൈൽ', kn: 'ಪ್ರೊಫೈಲ್', ta: 'சுயவிவரம்' },
  'nav.talk': { en: 'Talk to SunoSafe', hi: 'SunoSafe से बात करें', ml: 'SunoSafe-നോട് സംസാരിക്കുക', kn: 'SunoSafe ಜೊತೆ ಮಾತನಾಡಿ', ta: 'SunoSafe-உடன் பேசு' },
  'nav.skip': { en: 'Skip to content', hi: 'मुख्य भाग पर जाएँ', ml: 'ഉള്ളടക്കത്തിലേക്ക് പോകുക', kn: 'ವಿಷಯಕ್ಕೆ ಹೋಗಿ', ta: 'உள்ளடக்கத்திற்குச் செல்' },
  'nav.back': { en: 'Back to home', hi: 'होम पर वापस', ml: 'ഹോമിലേക്ക് മടങ്ങുക', kn: 'ಮುಖಪುಟಕ್ಕೆ ಹಿಂತಿರುಗಿ', ta: 'முகப்புக்குத் திரும்பு' },
  'title.default': { en: 'Scam guardian', hi: 'धोखाधड़ी से रक्षक', ml: 'തട്ടിപ്പ് സംരക്ഷകൻ', kn: 'ವಂಚನೆ ರಕ್ಷಕ', ta: 'மோசடிக் காவலர்' },
  'title.dashboard': { en: 'Security Operations (Mini-SIEM)', hi: 'सुरक्षा केंद्र (Mini-SIEM)', ml: 'സുരക്ഷാ കേന്ദ്രം (Mini-SIEM)', kn: 'ಭದ್ರತಾ ಕೇಂದ್ರ (Mini-SIEM)', ta: 'பாதுகாப்பு மையம் (Mini-SIEM)' },
  'title.scam': { en: 'Get help', hi: 'मदद लें', ml: 'സഹായം നേടുക', kn: 'ಸಹಾಯ ಪಡೆಯಿರಿ', ta: 'உதவி பெறு' },
  'title.safety': { en: 'Calls', hi: 'कॉल', ml: 'കോളുകൾ', kn: 'ಕರೆಗಳು', ta: 'அழைப்புகள்' },
  loading: { en: 'Loading…', hi: 'लोड हो रहा है…', ml: 'ലോഡ് ചെയ്യുന്നു…', kn: 'ಲೋಡ್ ಆಗುತ್ತಿದೆ…', ta: 'ஏற்றுகிறது…' },

  // ---- home
  'home.heroTitle': { en: 'Your personal call guardian', hi: 'आपका निजी कॉल रक्षक', ml: 'നിങ്ങളുടെ സ്വന്തം കോൾ സംരക്ഷകൻ', kn: 'ನಿಮ್ಮ ವೈಯಕ್ತಿಕ ಕರೆ ರಕ್ಷಕ', ta: 'உங்கள் தனிப்பட்ட அழைப்புக் காவலர்' },
  'home.heroText': {
    en: 'Checks messages, links and callers, and warns you out loud in your language.',
    hi: 'संदेश, लिंक और कॉल करने वालों की जाँच करता है, और आपकी भाषा में बोलकर चेतावनी देता है।',
    ml: 'സന്ദേശങ്ങളും ലിങ്കുകളും വിളിക്കുന്നവരെയും പരിശോധിച്ച്, നിങ്ങളുടെ ഭാഷയിൽ ഉറക്കെ മുന്നറിയിപ്പ് നൽകുന്നു.',
    kn: 'ಸಂದೇಶಗಳು, ಲಿಂಕ್‌ಗಳು ಮತ್ತು ಕರೆ ಮಾಡುವವರನ್ನು ಪರಿಶೀಲಿಸಿ, ನಿಮ್ಮ ಭಾಷೆಯಲ್ಲಿ ಜೋರಾಗಿ ಎಚ್ಚರಿಸುತ್ತದೆ.',
    ta: 'செய்திகள், இணைப்புகள், அழைப்பவர்களைச் சரிபார்த்து, உங்கள் மொழியில் சத்தமாக எச்சரிக்கிறது.',
  },
  'home.shieldOn': { en: 'Checks messages, links and callers', hi: 'संदेश, लिंक और कॉल करने वालों की जाँच चालू है', ml: 'സന്ദേശങ്ങൾ, ലിങ്കുകൾ, വിളിക്കുന്നവർ പരിശോധിക്കുന്നു', kn: 'ಸಂದೇಶ, ಲಿಂಕ್ ಮತ್ತು ಕರೆ ಮಾಡುವವರ ಪರಿಶೀಲನೆ ಚಾಲೂ', ta: 'செய்திகள், இணைப்புகள், அழைப்பவர்கள் சரிபார்க்கப்படுகின்றன' },
  'home.shieldOff': { en: 'Paused: checks are switched off', hi: 'रुका हुआ: जाँच बंद है', ml: 'നിർത്തിവച്ചു: പരിശോധന ഓഫാണ്', kn: 'ನಿಲ್ಲಿಸಲಾಗಿದೆ: ಪರಿಶೀಲನೆ ಆಫ್ ಆಗಿದೆ', ta: 'இடைநிறுத்தம்: சரிபார்ப்பு அணைக்கப்பட்டுள்ளது' },
  'home.callHistory': { en: 'Call history', hi: 'कॉल इतिहास', ml: 'കോൾ ചരിത്രം', kn: 'ಕರೆ ಇತಿಹಾಸ', ta: 'அழைப்பு வரலாறு' },
  'home.threatLogs': { en: 'Threat logs', hi: 'खतरे का रिकॉर्ड', ml: 'ഭീഷണി രേഖകൾ', kn: 'ಅಪಾಯದ ದಾಖಲೆಗಳು', ta: 'அச்சுறுத்தல் பதிவுகள்' },
  'home.dashboard': { en: 'SIEM dashboard', hi: 'SIEM डैशबोर्ड', ml: 'SIEM ഡാഷ്ബോർഡ്', kn: 'SIEM ಡ್ಯಾಶ್‌ಬೋರ್ಡ್', ta: 'SIEM டாஷ்போர்டு' },
  'home.settings': { en: 'Settings', hi: 'सेटिंग्स', ml: 'ക്രമീകരണങ്ങൾ', kn: 'ಸೆಟ್ಟಿಂಗ್‌ಗಳು', ta: 'அமைப்புகள்' },
  'home.checkMessage': { en: 'Check a message', hi: 'संदेश जाँचें', ml: 'സന്ദേശം പരിശോധിക്കുക', kn: 'ಸಂದೇಶ ಪರಿಶೀಲಿಸಿ', ta: 'செய்தியைச் சரிபார்' },
  'home.checkLink': { en: 'Check a link', hi: 'लिंक जाँचें', ml: 'ലിങ്ക് പരിശോധിക്കുക', kn: 'ಲಿಂಕ್ ಪರಿಶೀಲಿಸಿ', ta: 'இணைப்பைச் சரிபார்' },
  'home.drill': { en: 'Practise: scam call drill', hi: 'अभ्यास: धोखाधड़ी कॉल से बचना', ml: 'പരിശീലനം: തട്ടിപ്പ് കോൾ', kn: 'ಅಭ್ಯಾಸ: ವಂಚನೆ ಕರೆ', ta: 'பயிற்சி: மோசடி அழைப்பு' },
  'home.recent': { en: 'Recent activity', hi: 'हाल की गतिविधि', ml: 'സമീപകാല പ്രവർത്തനം', kn: 'ಇತ್ತೀಚಿನ ಚಟುವಟಿಕೆ', ta: 'சமீபத்திய செயல்பாடு' },
  'home.viewAll': { en: 'View all', hi: 'सब देखें', ml: 'എല്ലാം കാണുക', kn: 'ಎಲ್ಲವನ್ನೂ ನೋಡಿ', ta: 'அனைத்தையும் பார்' },
  'home.nothing': {
    en: 'Nothing suspicious in the last 7 days.', hi: 'पिछले 7 दिनों में कुछ भी संदिग्ध नहीं मिला।',
    ml: 'കഴിഞ്ഞ 7 ദിവസത്തിൽ സംശയാസ്പദമായ ഒന്നുമില്ല.', kn: 'ಕಳೆದ 7 ದಿನಗಳಲ್ಲಿ ಅನುಮಾನಾಸ್ಪದವಾದದ್ದು ಏನೂ ಇಲ್ಲ.',
    ta: 'கடந்த 7 நாட்களில் சந்தேகத்திற்குரியது எதுவும் இல்லை.',
  },
  'home.scamCall': { en: 'Scam call', hi: 'धोखाधड़ी कॉल', ml: 'തട്ടിപ്പ് കോൾ', kn: 'ವಂಚನೆ ಕರೆ', ta: 'மோசடி அழைப்பு' },
  'home.suspiciousCall': { en: 'Suspicious call', hi: 'संदिग्ध कॉल', ml: 'സംശയാസ്പദമായ കോൾ', kn: 'ಅನುಮಾನಾಸ್ಪದ ಕರೆ', ta: 'சந்தேகமான அழைப்பு' },
  'home.scammed': { en: 'I was scammed', hi: 'मेरे साथ धोखा हुआ', ml: 'ഞാൻ തട്ടിപ്പിനിരയായി', kn: 'ನಾನು ವಂಚನೆಗೆ ಒಳಗಾದೆ', ta: 'நான் ஏமாற்றப்பட்டேன்' },
  'home.call1930': { en: 'Call 1930', hi: '1930 पर कॉल करें', ml: '1930-ൽ വിളിക്കുക', kn: '1930ಗೆ ಕರೆ ಮಾಡಿ', ta: '1930-ஐ அழை' },

  // ---- settings
  'set.shield': { en: 'SunoSafe shield', hi: 'SunoSafe सुरक्षा', ml: 'SunoSafe സംരക്ഷണം', kn: 'SunoSafe ರಕ್ಷಣೆ', ta: 'SunoSafe பாதுகாப்பு' },
  'set.shieldHint': {
    en: 'When off, SunoSafe checks nothing and sends nothing.', hi: 'बंद होने पर SunoSafe न कुछ जाँचता है, न कुछ भेजता है।',
    ml: 'ഓഫാക്കിയാൽ SunoSafe ഒന്നും പരിശോധിക്കുകയോ അയയ്ക്കുകയോ ചെയ്യില്ല.', kn: 'ಆಫ್ ಆಗಿದ್ದಾಗ SunoSafe ಏನನ್ನೂ ಪರಿಶೀಲಿಸುವುದಿಲ್ಲ, ಏನನ್ನೂ ಕಳುಹಿಸುವುದಿಲ್ಲ.',
    ta: 'அணைத்திருக்கும்போது SunoSafe எதையும் சரிபார்க்காது, எதையும் அனுப்பாது.',
  },
  'set.vibrate': { en: 'Vibrate on danger', hi: 'खतरे पर वाइब्रेट करें', ml: 'അപകടമുണ്ടെങ്കിൽ വൈബ്രേറ്റ് ചെയ്യുക', kn: 'ಅಪಾಯವಿದ್ದಾಗ ಕಂಪಿಸು', ta: 'ஆபத்தில் அதிர்வு' },
  'set.vibrateHint': {
    en: 'The phone buzzes when something dangerous is found.', hi: 'कुछ खतरनाक मिलने पर फ़ोन वाइब्रेट करता है।',
    ml: 'അപകടകരമായ എന്തെങ്കിലും കണ്ടാൽ ഫോൺ വൈബ്രേറ്റ് ചെയ്യും.', kn: 'ಅಪಾಯಕಾರಿ ಏನಾದರೂ ಕಂಡರೆ ಫೋನ್ ಕಂಪಿಸುತ್ತದೆ.',
    ta: 'ஆபத்தானது கண்டறியப்பட்டால் தொலைபேசி அதிரும்.',
  },
  'set.textSize': { en: 'Text size', hi: 'अक्षर का आकार', ml: 'അക്ഷര വലിപ്പം', kn: 'ಅಕ್ಷರದ ಗಾತ್ರ', ta: 'எழுத்து அளவு' },
  'set.normal': { en: 'Normal', hi: 'सामान्य', ml: 'സാധാരണ', kn: 'ಸಾಮಾನ್ಯ', ta: 'சாதாரணம்' },
  'set.large': { en: 'Large', hi: 'बड़ा', ml: 'വലുത്', kn: 'ದೊಡ್ಡದು', ta: 'பெரியது' },
  'set.xlarge': { en: 'Largest', hi: 'सबसे बड़ा', ml: 'ഏറ്റവും വലുത്', kn: 'ಅತಿ ದೊಡ್ಡದು', ta: 'மிகப் பெரியது' },
  'set.callSafety': { en: 'Call safety: report a call, demos', hi: 'कॉल सुरक्षा: कॉल की शिकायत, डेमो', ml: 'കോൾ സുരക്ഷ: കോൾ റിപ്പോർട്ട്, ഡെമോ', kn: 'ಕರೆ ಸುರಕ್ಷತೆ: ಕರೆ ವರದಿ, ಡೆಮೊ', ta: 'அழைப்புப் பாதுகாப்பு: அழைப்பைப் புகாரளி, டெமோ' },
  'set.language': { en: 'Language', hi: 'भाषा', ml: 'ഭാഷ', kn: 'ಭಾಷೆ', ta: 'மொழி' },
  'set.languageHint': {
    en: 'Screens, replies and the voice use this language. SunoSafe listens in English, Hindi, Kannada and Tamil; Malayalam listening needs an extra speech service.',
    hi: 'स्क्रीन, जवाब और आवाज़ इसी भाषा में होंगे। SunoSafe अंग्रेज़ी, हिंदी, कन्नड़ और तमिल में सुन सकता है; मलयालम सुनने के लिए एक और भाषण सेवा चाहिए।',
    ml: 'സ്ക്രീനും മറുപടികളും ശബ്ദവും ഈ ഭാഷയിലായിരിക്കും. SunoSafe ഇംഗ്ലീഷ്, ഹിന്ദി, കന്നഡ, തമിഴ് എന്നിവ കേട്ട് മനസ്സിലാക്കും; മലയാളം കേൾക്കാൻ ഒരു അധിക സ്പീച്ച് സേവനം വേണം.',
    kn: 'ಪರದೆ, ಉತ್ತರಗಳು ಮತ್ತು ಧ್ವನಿ ಈ ಭಾಷೆಯಲ್ಲಿರುತ್ತವೆ. SunoSafe ಇಂಗ್ಲಿಷ್, ಹಿಂದಿ, ಕನ್ನಡ ಮತ್ತು ತಮಿಳಿನಲ್ಲಿ ಕೇಳಿಸಿಕೊಳ್ಳುತ್ತದೆ; ಮಲಯಾಳಂ ಕೇಳಲು ಹೆಚ್ಚುವರಿ ಧ್ವನಿ ಸೇವೆ ಬೇಕು.',
    ta: 'திரை, பதில்கள், குரல் அனைத்தும் இந்த மொழியில் இருக்கும். SunoSafe ஆங்கிலம், இந்தி, கன்னடம், தமிழில் கேட்கும்; மலையாளம் கேட்க கூடுதல் பேச்சுச் சேவை தேவை.',
  },
  'set.homeScreen': { en: 'Put SunoSafe on your home screen', hi: 'SunoSafe को होम स्क्रीन पर रखें', ml: 'SunoSafe ഹോം സ്ക്രീനിൽ ചേർക്കുക', kn: 'SunoSafe ಅನ್ನು ಹೋಮ್ ಸ್ಕ್ರೀನ್‌ಗೆ ಸೇರಿಸಿ', ta: 'SunoSafe-ஐ முகப்புத் திரையில் வை' },
  'set.homeScreenText': {
    en: 'This also adds SunoSafe to the Share menu of WhatsApp and Messages.', hi: 'इससे SunoSafe, WhatsApp और Messages के Share मेनू में भी आ जाता है।',
    ml: 'ഇതോടെ WhatsApp-ലെയും Messages-ലെയും Share മെനുവിലും SunoSafe വരും.', kn: 'ಇದರಿಂದ WhatsApp ಮತ್ತು Messages ನ Share ಮೆನುವಿನಲ್ಲೂ SunoSafe ಕಾಣಿಸುತ್ತದೆ.',
    ta: 'இதனால் WhatsApp, Messages-இன் Share பட்டியலிலும் SunoSafe சேரும்.',
  },
  'set.howInstall': { en: 'How to install', hi: 'कैसे इंस्टॉल करें', ml: 'എങ്ങനെ ഇൻസ്റ്റാൾ ചെയ്യാം', kn: 'ಹೇಗೆ ಇನ್‌ಸ್ಟಾಲ್ ಮಾಡುವುದು', ta: 'நிறுவுவது எப்படி' },
  'set.install1': { en: 'In Chrome, tap the ⋮ menu at the top right.', hi: 'Chrome में ऊपर दाईं ओर ⋮ मेनू दबाएँ।', ml: 'Chrome-ൽ മുകളിൽ വലതുവശത്തുള്ള ⋮ മെനു തൊടുക.', kn: 'Chrome ನಲ್ಲಿ ಮೇಲಿನ ಬಲಭಾಗದ ⋮ ಮೆನು ಒತ್ತಿ.', ta: 'Chrome-இல் மேலே வலதுபுறம் உள்ள ⋮ மெனுவைத் தொடவும்.' },
  'set.install2': { en: 'Tap "Add to Home screen", then "Install".', hi: '"Add to Home screen" दबाएँ, फिर "Install"।', ml: '"Add to Home screen" തൊട്ട്, പിന്നെ "Install" തൊടുക.', kn: '"Add to Home screen" ಒತ್ತಿ, ನಂತರ "Install" ಒತ್ತಿ.', ta: '"Add to Home screen" தொட்டு, பிறகு "Install" தொடவும்.' },
  'set.install3': { en: 'Open SunoSafe from its new icon.', hi: 'नए आइकन से SunoSafe खोलें।', ml: 'പുതിയ ഐക്കണിൽ നിന്ന് SunoSafe തുറക്കുക.', kn: 'ಹೊಸ ಐಕಾನ್‌ನಿಂದ SunoSafe ತೆರೆಯಿರಿ.', ta: 'புதிய ஐகானிலிருந்து SunoSafe-ஐத் திறக்கவும்.' },
  'set.lock': { en: 'Lock SunoSafe', hi: 'SunoSafe लॉक करें', ml: 'SunoSafe ലോക്ക് ചെയ്യുക', kn: 'SunoSafe ಲಾಕ್ ಮಾಡಿ', ta: 'SunoSafe-ஐப் பூட்டு' },

  // ---- Android companion card
  'comp.title': { en: 'Automatic scam warnings', hi: 'अपने-आप धोखाधड़ी चेतावनी', ml: 'സ്വയമേവ തട്ടിപ്പ് മുന്നറിയിപ്പ്', kn: 'ಸ್ವಯಂಚಾಲಿತ ವಂಚನೆ ಎಚ್ಚರಿಕೆ', ta: 'தானியங்கி மோசடி எச்சரிக்கை' },
  'comp.text': {
    en: 'The SunoSafe Android app watches new WhatsApp and SMS notifications and warns you aloud when one looks like a scam. Ordinary messages never leave your phone.',
    hi: 'SunoSafe Android ऐप नए WhatsApp और SMS सूचनाओं पर नज़र रखता है और धोखाधड़ी लगने पर बोलकर चेतावनी देता है। आम संदेश आपके फ़ोन से बाहर नहीं जाते।',
    ml: 'SunoSafe Android ആപ്പ് പുതിയ WhatsApp, SMS അറിയിപ്പുകൾ നിരീക്ഷിച്ച്, തട്ടിപ്പ് പോലെ തോന്നിയാൽ ഉറക്കെ മുന്നറിയിപ്പ് നൽകുന്നു. സാധാരണ സന്ദേശങ്ങൾ നിങ്ങളുടെ ഫോണിൽ നിന്ന് പുറത്തുപോകില്ല.',
    kn: 'SunoSafe Android ಆ್ಯಪ್ ಹೊಸ WhatsApp ಮತ್ತು SMS ಅಧಿಸೂಚನೆಗಳನ್ನು ಗಮನಿಸಿ, ವಂಚನೆಯಂತೆ ಕಂಡರೆ ಜೋರಾಗಿ ಎಚ್ಚರಿಸುತ್ತದೆ. ಸಾಮಾನ್ಯ ಸಂದೇಶಗಳು ನಿಮ್ಮ ಫೋನ್‌ನಿಂದ ಹೊರಗೆ ಹೋಗುವುದಿಲ್ಲ.',
    ta: 'SunoSafe Android செயலி புதிய WhatsApp, SMS அறிவிப்புகளைக் கவனித்து, மோசடி போல் தெரிந்தால் சத்தமாக எச்சரிக்கும். சாதாரண செய்திகள் உங்கள் தொலைபேசியை விட்டு வெளியேறாது.',
  },
  'comp.s1': { en: 'Install the Android app.', hi: 'Android ऐप इंस्टॉल करें।', ml: 'Android ആപ്പ് ഇൻസ്റ്റാൾ ചെയ്യുക.', kn: 'Android ಆ್ಯಪ್ ಇನ್‌ಸ್ಟಾಲ್ ಮಾಡಿ.', ta: 'Android செயலியை நிறுவவும்.' },
  'comp.s2': { en: 'Open it and turn on notification access.', hi: 'उसे खोलें और notification access चालू करें।', ml: 'അത് തുറന്ന് notification access ഓണാക്കുക.', kn: 'ಅದನ್ನು ತೆರೆದು notification access ಆನ್ ಮಾಡಿ.', ta: 'அதைத் திறந்து notification access-ஐ இயக்கவும்.' },
  'comp.s3': { en: 'Come back here and tap Connect.', hi: 'यहाँ लौटकर "जोड़ें" दबाएँ।', ml: 'ഇവിടെ തിരിച്ചെത്തി "ബന്ധിപ്പിക്കുക" തൊടുക.', kn: 'ಇಲ್ಲಿಗೆ ಹಿಂತಿರುಗಿ "ಸಂಪರ್ಕಿಸಿ" ಒತ್ತಿ.', ta: 'இங்கே திரும்பி "இணை" தொடவும்.' },
  'comp.download': { en: '1. Download the Android app', hi: '1. Android ऐप डाउनलोड करें', ml: '1. Android ആപ്പ് ഡൗൺലോഡ് ചെയ്യുക', kn: '1. Android ಆ್ಯಪ್ ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ', ta: '1. Android செயலியைப் பதிவிறக்கு' },
  'comp.connect': { en: '3. Connect Android app', hi: '3. Android ऐप जोड़ें', ml: '3. Android ആപ്പ് ബന്ധിപ്പിക്കുക', kn: '3. Android ಆ್ಯಪ್ ಸಂಪರ್ಕಿಸಿ', ta: '3. Android செயலியை இணை' },
  'comp.notOpened': {
    en: 'If nothing opened, install the SunoSafe Android app first (step 1).', hi: 'अगर कुछ नहीं खुला, तो पहले SunoSafe Android ऐप इंस्टॉल करें (चरण 1)।',
    ml: 'ഒന്നും തുറന്നില്ലെങ്കിൽ, ആദ്യം SunoSafe Android ആപ്പ് ഇൻസ്റ്റാൾ ചെയ്യുക (ഘട്ടം 1).', kn: 'ಏನೂ ತೆರೆಯದಿದ್ದರೆ, ಮೊದಲು SunoSafe Android ಆ್ಯಪ್ ಇನ್‌ಸ್ಟಾಲ್ ಮಾಡಿ (ಹಂತ 1).',
    ta: 'எதுவும் திறக்கவில்லை என்றால், முதலில் SunoSafe Android செயலியை நிறுவவும் (படி 1).',
  },

  // ---- honesty tags
  'tag.real': { en: 'Working', hi: 'काम करता है', ml: 'പ്രവർത്തിക്കുന്നു', kn: 'ಕೆಲಸ ಮಾಡುತ್ತದೆ', ta: 'செயல்படுகிறது' },
  'tag.simulated': { en: 'Simulated demo', hi: 'नकली डेमो', ml: 'മാതൃകാ ഡെമോ', kn: 'ಅನುಕರಣೆ ಡೆಮೊ', ta: 'மாதிரி டெமோ' },
  'tag.planned': { en: 'Planned for Android app', hi: 'Android ऐप के लिए योजना में', ml: 'Android ആപ്പിനായി ആസൂത്രണം ചെയ്തത്', kn: 'Android ಆ್ಯಪ್‌ಗೆ ಯೋಜಿಸಲಾಗಿದೆ', ta: 'Android செயலிக்குத் திட்டமிடப்பட்டது' },
  'tag.setup': { en: 'Needs a phone number', hi: 'फ़ोन नंबर चाहिए', ml: 'ഫോൺ നമ്പർ വേണം', kn: 'ಫೋನ್ ಸಂಖ್ಯೆ ಬೇಕು', ta: 'தொலைபேசி எண் தேவை' },

  // ---- verdict
  'verdict.danger': { en: 'Danger', hi: 'खतरा', ml: 'അപകടം', kn: 'ಅಪಾಯ', ta: 'ஆபத்து' },
  'verdict.caution': { en: 'Be careful', hi: 'सावधान रहें', ml: 'ശ്രദ്ധിക്കുക', kn: 'ಎಚ್ಚರಿಕೆ ವಹಿಸಿ', ta: 'கவனமாக இருங்கள்' },
  'verdict.ok': { en: 'No known problems found', hi: 'कोई ज्ञात समस्या नहीं मिली', ml: 'അറിയപ്പെടുന്ന പ്രശ്നങ്ങളൊന്നും കണ്ടില്ല', kn: 'ತಿಳಿದ ಸಮಸ್ಯೆಗಳೇನೂ ಕಂಡುಬಂದಿಲ್ಲ', ta: 'அறியப்பட்ட சிக்கல்கள் எதுவும் இல்லை' },
  'verdict.adviceDanger': {
    en: '', hi: 'लिंक न खोलें, पैसे न भेजें, और OTP या PIN कभी किसी को न बताएँ।',
    ml: 'ലിങ്ക് തുറക്കരുത്, പണം അയയ്ക്കരുത്, OTP-യോ PIN-ഓ ഒരിക്കലും ആരോടും പറയരുത്.',
    kn: 'ಲಿಂಕ್ ತೆರೆಯಬೇಡಿ, ಹಣ ಕಳುಹಿಸಬೇಡಿ, OTP ಅಥವಾ PIN ಅನ್ನು ಯಾರಿಗೂ ಹೇಳಬೇಡಿ.',
    ta: 'இணைப்பைத் திறக்காதீர்கள், பணம் அனுப்பாதீர்கள், OTP அல்லது PIN-ஐ யாரிடமும் சொல்லாதீர்கள்.',
  },
  'verdict.adviceCaution': {
    en: '', hi: 'OTP या PIN न बताएँ। बैंक या उस व्यक्ति से खुद, किसी भरोसेमंद नंबर पर पूछें।',
    ml: 'OTP-യോ PIN-ഓ പറയരുത്. ബാങ്കിനോടോ ആ വ്യക്തിയോടോ നിങ്ങൾക്ക് വിശ്വാസമുള്ള നമ്പറിൽ സ്വയം ചോദിക്കുക.',
    kn: 'OTP ಅಥವಾ PIN ಹೇಳಬೇಡಿ. ಬ್ಯಾಂಕ್ ಅಥವಾ ಆ ವ್ಯಕ್ತಿಯನ್ನು ನೀವು ನಂಬುವ ಸಂಖ್ಯೆಯಲ್ಲಿ ನೀವೇ ಕೇಳಿ.',
    ta: 'OTP அல்லது PIN-ஐச் சொல்லாதீர்கள். வங்கியிடமோ அந்த நபரிடமோ நீங்கள் நம்பும் எண்ணில் நீங்களே கேளுங்கள்.',
  },
  'verdict.adviceOk': {
    en: '', hi: 'SunoSafe को कोई ज्ञात चेतावनी संकेत नहीं मिला। इसका मतलब यह नहीं कि यह पक्का सुरक्षित है।',
    ml: 'അറിയപ്പെടുന്ന മുന്നറിയിപ്പ് അടയാളങ്ങളൊന്നും SunoSafe കണ്ടില്ല. ഇത് സുരക്ഷിതമാണെന്ന് ഉറപ്പല്ല.',
    kn: 'SunoSafe ಗೆ ತಿಳಿದ ಎಚ್ಚರಿಕೆ ಚಿಹ್ನೆಗಳು ಕಂಡುಬಂದಿಲ್ಲ. ಇದು ಸುರಕ್ಷಿತ ಎಂದು ಖಚಿತವಲ್ಲ.',
    ta: 'அறியப்பட்ட எச்சரிக்கை அறிகுறிகள் எதையும் SunoSafe காணவில்லை. இது பாதுகாப்பானது என்பதற்கு உறுதி இல்லை.',
  },
  'verdict.englishNote': { en: '', hi: 'नीचे का विवरण अंग्रेज़ी में है।', ml: 'താഴെയുള്ള വിശദാംശങ്ങൾ ഇംഗ്ലീഷിലാണ്.', kn: 'ಕೆಳಗಿನ ವಿವರಗಳು ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿವೆ.', ta: 'கீழே உள்ள விவரங்கள் ஆங்கிலத்தில் உள்ளன.' },
  'verdict.why': { en: 'Why', hi: 'क्यों', ml: 'എന്തുകൊണ്ട്', kn: 'ಏಕೆ', ta: 'ஏன்' },
  'verdict.couldNot': { en: 'What I could not check', hi: 'जो मैं जाँच नहीं सका', ml: 'എനിക്ക് പരിശോധിക്കാൻ കഴിയാത്തത്', kn: 'ನಾನು ಪರಿಶೀಲಿಸಲಾಗದವು', ta: 'என்னால் சரிபார்க்க முடியாதவை' },
  'confirm.no': { en: 'No, go back', hi: 'नहीं, वापस जाएँ', ml: 'വേണ്ട, തിരികെ പോകുക', kn: 'ಬೇಡ, ಹಿಂದೆ ಹೋಗಿ', ta: 'வேண்டாம், திரும்பிச் செல்' },

  // ---- check a message
  'check.intro': {
    en: 'Bring the message here from WhatsApp or SMS, or let the SunoSafe Android app check it for you.',
    hi: 'WhatsApp या SMS से संदेश यहाँ लाएँ, या SunoSafe Android ऐप को आपके लिए जाँचने दें।',
    ml: 'WhatsApp-ൽ നിന്നോ SMS-ൽ നിന്നോ സന്ദേശം ഇവിടെ കൊണ്ടുവരിക, അല്ലെങ്കിൽ SunoSafe Android ആപ്പ് നിങ്ങൾക്കായി പരിശോധിക്കട്ടെ.',
    kn: 'WhatsApp ಅಥವಾ SMS ನಿಂದ ಸಂದೇಶವನ್ನು ಇಲ್ಲಿಗೆ ತನ್ನಿ, ಅಥವಾ SunoSafe Android ಆ್ಯಪ್ ನಿಮಗಾಗಿ ಪರಿಶೀಲಿಸಲಿ.',
    ta: 'WhatsApp அல்லது SMS-இலிருந்து செய்தியை இங்கே கொண்டு வாருங்கள், அல்லது SunoSafe Android செயலி உங்களுக்காகச் சரிபார்க்கட்டும்.',
  },
  'check.get': { en: 'Get the message', hi: 'संदेश लाएँ', ml: 'സന്ദേശം എടുക്കുക', kn: 'ಸಂದೇಶ ತನ್ನಿ', ta: 'செய்தியை எடு' },
  'check.step1': {
    en: 'Open the chat below and press and hold the message.', hi: 'नीचे से चैट खोलें और संदेश को दबाकर रखें।',
    ml: 'താഴെ നിന്ന് ചാറ്റ് തുറന്ന് സന്ദേശം അമർത്തിപ്പിടിക്കുക.', kn: 'ಕೆಳಗಿನಿಂದ ಚಾಟ್ ತೆರೆದು ಸಂದೇಶವನ್ನು ಒತ್ತಿ ಹಿಡಿಯಿರಿ.',
    ta: 'கீழே உள்ள அரட்டையைத் திறந்து செய்தியை அழுத்திப் பிடிக்கவும்.',
  },
  'check.step2': {
    en: 'Tap Copy (WhatsApp: the copy icon at the top).', hi: '"Copy" दबाएँ (WhatsApp में: ऊपर कॉपी आइकन)।',
    ml: '"Copy" തൊടുക (WhatsApp-ൽ: മുകളിലെ കോപ്പി ഐക്കൺ).', kn: '"Copy" ಒತ್ತಿ (WhatsApp ನಲ್ಲಿ: ಮೇಲಿನ ಕಾಪಿ ಐಕಾನ್).',
    ta: '"Copy" தொடவும் (WhatsApp-இல்: மேலே உள்ள நகல் ஐகான்).',
  },
  'check.step3': {
    en: 'Come back here and tap Paste, then Check this message.', hi: 'यहाँ लौटकर "चिपकाएँ" दबाएँ, फिर "यह संदेश जाँचें"।',
    ml: 'ഇവിടെ തിരിച്ചെത്തി "ഒട്ടിക്കുക" തൊടുക, പിന്നെ "ഈ സന്ദേശം പരിശോധിക്കുക".', kn: 'ಇಲ್ಲಿಗೆ ಹಿಂತಿರುಗಿ "ಅಂಟಿಸಿ" ಒತ್ತಿ, ನಂತರ "ಈ ಸಂದೇಶ ಪರಿಶೀಲಿಸಿ".',
    ta: 'இங்கே திரும்பி "ஒட்டு" தொட்டு, பிறகு "இந்தச் செய்தியைச் சரிபார்".',
  },
  'check.openWa': { en: 'Open WhatsApp', hi: 'WhatsApp खोलें', ml: 'WhatsApp തുറക്കുക', kn: 'WhatsApp ತೆರೆಯಿರಿ', ta: 'WhatsApp-ஐத் திற' },
  'check.openSms': { en: 'Open Messages', hi: 'Messages खोलें', ml: 'Messages തുറക്കുക', kn: 'Messages ತೆರೆಯಿರಿ', ta: 'Messages-ஐத் திற' },
  'check.faster': {
    en: 'Faster with the SunoSafe Android app: press and hold the message → Share → SunoSafe, and it is checked and the answer is spoken at once. With screen checking switched on, the app also checks messages you simply open or scroll, without copying anything.',
    hi: 'SunoSafe Android ऐप से और तेज़: संदेश दबाकर रखें → Share → SunoSafe, और तुरंत जाँच होकर जवाब बोला जाता है। "स्क्रीन जाँच" चालू हो तो ऐप उन संदेशों को भी जाँचता है जिन्हें आप बस खोलते या स्क्रॉल करते हैं, बिना कुछ कॉपी किए।',
    ml: 'SunoSafe Android ആപ്പ് ഉപയോഗിച്ചാൽ കൂടുതൽ വേഗം: സന്ദേശം അമർത്തിപ്പിടിക്കുക → Share → SunoSafe; ഉടൻ പരിശോധിച്ച് മറുപടി പറയും. "സ്ക്രീൻ പരിശോധന" ഓണാണെങ്കിൽ, നിങ്ങൾ തുറക്കുകയോ സ്ക്രോൾ ചെയ്യുകയോ ചെയ്യുന്ന സന്ദേശങ്ങളും ഒന്നും കോപ്പി ചെയ്യാതെ ആപ്പ് പരിശോധിക്കും.',
    kn: 'SunoSafe Android ಆ್ಯಪ್‌ನಿಂದ ಇನ್ನೂ ವೇಗ: ಸಂದೇಶವನ್ನು ಒತ್ತಿ ಹಿಡಿಯಿರಿ → Share → SunoSafe; ತಕ್ಷಣ ಪರಿಶೀಲಿಸಿ ಉತ್ತರವನ್ನು ಹೇಳುತ್ತದೆ. "ಪರದೆ ಪರಿಶೀಲನೆ" ಆನ್ ಆಗಿದ್ದರೆ, ನೀವು ತೆರೆಯುವ ಅಥವಾ ಸ್ಕ್ರಾಲ್ ಮಾಡುವ ಸಂದೇಶಗಳನ್ನೂ ಏನನ್ನೂ ಕಾಪಿ ಮಾಡದೆ ಆ್ಯಪ್ ಪರಿಶೀಲಿಸುತ್ತದೆ.',
    ta: 'SunoSafe Android செயலியுடன் இன்னும் வேகம்: செய்தியை அழுத்திப் பிடி → Share → SunoSafe; உடனே சரிபார்த்து பதிலைச் சொல்லும். "திரைச் சரிபார்ப்பு" இயக்கத்தில் இருந்தால், நீங்கள் திறக்கும் அல்லது உருட்டும் செய்திகளையும் எதையும் நகலெடுக்காமல் செயலி சரிபார்க்கும்.',
  },
  'check.label': { en: 'Message', hi: 'संदेश', ml: 'സന്ദേശം', kn: 'ಸಂದೇಶ', ta: 'செய்தி' },
  'check.placeholder': { en: 'Paste the message here', hi: 'संदेश यहाँ चिपकाएँ', ml: 'സന്ദേശം ഇവിടെ ഒട്ടിക്കുക', kn: 'ಸಂದೇಶವನ್ನು ಇಲ್ಲಿ ಅಂಟಿಸಿ', ta: 'செய்தியை இங்கே ஒட்டவும்' },
  'check.paste': { en: 'Paste', hi: 'चिपकाएँ', ml: 'ഒട്ടിക്കുക', kn: 'ಅಂಟಿಸಿ', ta: 'ஒட்டு' },
  'check.clear': { en: 'Clear', hi: 'साफ़ करें', ml: 'മായ്ക്കുക', kn: 'ಅಳಿಸಿ', ta: 'அழி' },
  'check.example': { en: 'Example', hi: 'उदाहरण', ml: 'ഉദാഹരണം', kn: 'ಉದಾಹರಣೆ', ta: 'எடுத்துக்காட்டு' },
  'check.exampleAria': {
    en: 'Fill in an example scam message to try', hi: 'आज़माने के लिए एक उदाहरण धोखाधड़ी संदेश भरें',
    ml: 'പരീക്ഷിക്കാൻ ഒരു മാതൃകാ തട്ടിപ്പ് സന്ദേശം ചേർക്കുക', kn: 'ಪ್ರಯತ್ನಿಸಲು ಒಂದು ಉದಾಹರಣೆ ವಂಚನೆ ಸಂದೇಶ ತುಂಬಿಸಿ',
    ta: 'முயற்சிக்க ஒரு எடுத்துக்காட்டு மோசடிச் செய்தியை நிரப்பு',
  },
  'check.submit': { en: 'Check this message', hi: 'यह संदेश जाँचें', ml: 'ഈ സന്ദേശം പരിശോധിക്കുക', kn: 'ಈ ಸಂದೇಶ ಪರಿಶೀಲಿಸಿ', ta: 'இந்தச் செய்தியைச் சரிபார்' },
  'check.busy': { en: 'Checking… this takes a few seconds', hi: 'जाँच हो रही है… कुछ सेकंड लगेंगे', ml: 'പരിശോധിക്കുന്നു… കുറച്ച് സെക്കൻഡ് എടുക്കും', kn: 'ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ… ಕೆಲವು ಸೆಕೆಂಡು ಬೇಕು', ta: 'சரிபார்க்கிறது… சில வினாடிகள் ஆகும்' },
  'check.signs': { en: 'Warning signs in the message', hi: 'संदेश में चेतावनी के संकेत', ml: 'സന്ദേശത്തിലെ മുന്നറിയിപ്പ് അടയാളങ്ങൾ', kn: 'ಸಂದೇಶದಲ್ಲಿನ ಎಚ್ಚರಿಕೆ ಚಿಹ್ನೆಗಳು', ta: 'செய்தியில் உள்ள எச்சரிக்கை அறிகுறிகள்' },
  'check.askVoice': { en: 'Ask SunoSafe about it by voice', hi: 'इसके बारे में SunoSafe से बोलकर पूछें', ml: 'ഇതിനെക്കുറിച്ച് SunoSafe-നോട് ശബ്ദത്തിൽ ചോദിക്കുക', kn: 'ಇದರ ಬಗ್ಗೆ SunoSafe ಅನ್ನು ಧ್ವನಿಯಲ್ಲಿ ಕೇಳಿ', ta: 'இதைப் பற்றி SunoSafe-இடம் குரலில் கேள்' },
  'check.clicked': {
    en: 'I already clicked or shared details', hi: 'मैंने पहले ही क्लिक किया या जानकारी दे दी',
    ml: 'ഞാൻ ഇതിനകം ക്ലിക്ക് ചെയ്തു അല്ലെങ്കിൽ വിവരങ്ങൾ പങ്കിട്ടു', kn: 'ನಾನು ಈಗಾಗಲೇ ಕ್ಲಿಕ್ ಮಾಡಿದ್ದೇನೆ ಅಥವಾ ವಿವರ ಹಂಚಿಕೊಂಡಿದ್ದೇನೆ',
    ta: 'நான் ஏற்கனவே கிளிக் செய்தேன் அல்லது விவரங்களைப் பகிர்ந்தேன்',
  },
  'check.paused': {
    en: 'Shield is paused. Turn it on in Settings to check messages.', hi: 'सुरक्षा रुकी हुई है। संदेश जाँचने के लिए सेटिंग्स में इसे चालू करें।',
    ml: 'സംരക്ഷണം നിർത്തിവച്ചിരിക്കുന്നു. സന്ദേശങ്ങൾ പരിശോധിക്കാൻ ക്രമീകരണങ്ങളിൽ ഓണാക്കുക.', kn: 'ರಕ್ಷಣೆ ನಿಲ್ಲಿಸಲಾಗಿದೆ. ಸಂದೇಶ ಪರಿಶೀಲಿಸಲು ಸೆಟ್ಟಿಂಗ್‌ಗಳಲ್ಲಿ ಆನ್ ಮಾಡಿ.',
    ta: 'பாதுகாப்பு இடைநிறுத்தப்பட்டுள்ளது. செய்திகளைச் சரிபார்க்க அமைப்புகளில் இயக்கவும்.',
  },
  'check.clipEmpty': {
    en: 'The clipboard is empty. Copy the message first.', hi: 'क्लिपबोर्ड खाली है। पहले संदेश कॉपी करें।',
    ml: 'ക്ലിപ്പ്ബോർഡ് ശൂന്യമാണ്. ആദ്യം സന്ദേശം കോപ്പി ചെയ്യുക.', kn: 'ಕ್ಲಿಪ್‌ಬೋರ್ಡ್ ಖಾಲಿ ಇದೆ. ಮೊದಲು ಸಂದೇಶ ಕಾಪಿ ಮಾಡಿ.',
    ta: 'கிளிப்போர்டு காலியாக உள்ளது. முதலில் செய்தியை நகலெடுக்கவும்.',
  },
  'check.pasteDenied': {
    en: 'Paste was not allowed. Press and hold in the box and choose Paste.', hi: 'चिपकाने की अनुमति नहीं मिली। बॉक्स में दबाकर रखें और Paste चुनें।',
    ml: 'ഒട്ടിക്കാൻ അനുവാദം ലഭിച്ചില്ല. ബോക്സിൽ അമർത്തിപ്പിടിച്ച് Paste തിരഞ്ഞെടുക്കുക.', kn: 'ಅಂಟಿಸಲು ಅನುಮತಿ ಸಿಗಲಿಲ್ಲ. ಬಾಕ್ಸ್‌ನಲ್ಲಿ ಒತ್ತಿ ಹಿಡಿದು Paste ಆಯ್ಕೆಮಾಡಿ.',
    ta: 'ஒட்ட அனுமதி இல்லை. பெட்டியில் அழுத்திப் பிடித்து Paste-ஐத் தேர்ந்தெடுக்கவும்.',
  },

  // ---- block a link
  'block.done': { en: 'Blocked. SunoSafe will refuse to open {site}.', hi: 'ब्लॉक हो गया। SunoSafe अब {site} नहीं खोलेगा।', ml: 'ബ്ലോക്ക് ചെയ്തു. SunoSafe ഇനി {site} തുറക്കില്ല.', kn: 'ಬ್ಲಾಕ್ ಮಾಡಲಾಗಿದೆ. SunoSafe ಇನ್ನು {site} ತೆರೆಯುವುದಿಲ್ಲ.', ta: 'தடுக்கப்பட்டது. SunoSafe இனி {site}-ஐத் திறக்காது.' },
  'block.busy': { en: 'Blocking…', hi: 'ब्लॉक हो रहा है…', ml: 'ബ്ലോക്ക് ചെയ്യുന്നു…', kn: 'ಬ್ಲಾಕ್ ಮಾಡಲಾಗುತ್ತಿದೆ…', ta: 'தடுக்கிறது…' },
  'block.btn': { en: 'Block {site}', hi: '{site} ब्लॉक करें', ml: '{site} ബ്ലോക്ക് ചെയ്യുക', kn: '{site} ಬ್ಲಾಕ್ ಮಾಡಿ', ta: '{site}-ஐத் தடு' },
  'block.title': { en: 'Block this link?', hi: 'यह लिंक ब्लॉक करें?', ml: 'ഈ ലിങ്ക് ബ്ലോക്ക് ചെയ്യണോ?', kn: 'ಈ ಲಿಂಕ್ ಬ್ಲಾಕ್ ಮಾಡಬೇಕೇ?', ta: 'இந்த இணைப்பைத் தடுக்கவா?' },
  'block.body': {
    en: 'SunoSafe will refuse to open {site} from now on. You can still see it in your incident list.',
    hi: 'अब से SunoSafe {site} नहीं खोलेगा। आप इसे अपनी घटना सूची में अब भी देख सकते हैं।',
    ml: 'ഇനി മുതൽ SunoSafe {site} തുറക്കില്ല. നിങ്ങളുടെ സംഭവ പട്ടികയിൽ ഇത് ഇപ്പോഴും കാണാം.',
    kn: 'ಇನ್ನು ಮುಂದೆ SunoSafe {site} ತೆರೆಯುವುದಿಲ್ಲ. ನಿಮ್ಮ ಘಟನೆ ಪಟ್ಟಿಯಲ್ಲಿ ಇದನ್ನು ಇನ್ನೂ ನೋಡಬಹುದು.',
    ta: 'இனி SunoSafe {site}-ஐத் திறக்காது. உங்கள் சம்பவப் பட்டியலில் இதை இன்னும் பார்க்கலாம்.',
  },
  'block.yes': { en: 'Yes, block it', hi: 'हाँ, ब्लॉक करें', ml: 'അതെ, ബ്ലോക്ക് ചെയ്യുക', kn: 'ಹೌದು, ಬ್ಲಾಕ್ ಮಾಡಿ', ta: 'ஆம், தடு' },
  'block.thisLink': { en: 'this link', hi: 'यह लिंक', ml: 'ഈ ലിങ്ക്', kn: 'ಈ ಲಿಂಕ್', ta: 'இந்த இணைப்பு' },

  // ---- check a link
  'links.title': { en: 'Check or open a link', hi: 'लिंक जाँचें या खोलें', ml: 'ലിങ്ക് പരിശോധിക്കുക അല്ലെങ്കിൽ തുറക്കുക', kn: 'ಲಿಂಕ್ ಪರಿಶೀಲಿಸಿ ಅಥವಾ ತೆರೆಯಿರಿ', ta: 'இணைப்பைச் சரிபார் அல்லது திற' },
  'links.intro': {
    en: 'SunoSafe looks at where a link really goes, how old the website is and whether its security certificate is valid.',
    hi: 'SunoSafe देखता है कि लिंक असल में कहाँ जाता है, वेबसाइट कितनी पुरानी है और उसका सुरक्षा प्रमाणपत्र सही है या नहीं।',
    ml: 'ലിങ്ക് യഥാർത്ഥത്തിൽ എവിടേക്ക് പോകുന്നു, വെബ്സൈറ്റിന് എത്ര പഴക്കമുണ്ട്, സുരക്ഷാ സർട്ടിഫിക്കറ്റ് സാധുവാണോ എന്നെല്ലാം SunoSafe നോക്കുന്നു.',
    kn: 'ಲಿಂಕ್ ನಿಜವಾಗಿ ಎಲ್ಲಿಗೆ ಹೋಗುತ್ತದೆ, ವೆಬ್‌ಸೈಟ್ ಎಷ್ಟು ಹಳೆಯದು, ಅದರ ಭದ್ರತಾ ಪ್ರಮಾಣಪತ್ರ ಸರಿಯಿದೆಯೇ ಎಂದು SunoSafe ನೋಡುತ್ತದೆ.',
    ta: 'இணைப்பு உண்மையில் எங்கே செல்கிறது, இணையதளம் எவ்வளவு பழையது, அதன் பாதுகாப்புச் சான்றிதழ் சரியானதா என்பதை SunoSafe பார்க்கிறது.',
  },
  'links.label': { en: 'Link', hi: 'लिंक', ml: 'ലിങ്ക്', kn: 'ಲಿಂಕ್', ta: 'இணைப்பு' },
  'links.placeholder': { en: 'Paste the link here', hi: 'लिंक यहाँ चिपकाएँ', ml: 'ലിങ്ക് ഇവിടെ ഒട്ടിക്കുക', kn: 'ಲಿಂಕ್ ಇಲ್ಲಿ ಅಂಟಿಸಿ', ta: 'இணைப்பை இங்கே ஒட்டவும்' },
  'links.investigate': { en: 'Investigate this link', hi: 'इस लिंक की जाँच करें', ml: 'ഈ ലിങ്ക് അന്വേഷിക്കുക', kn: 'ಈ ಲಿಂಕ್ ತನಿಖೆ ಮಾಡಿ', ta: 'இந்த இணைப்பை ஆராய்' },
  'links.investigating': { en: 'Investigating…', hi: 'जाँच हो रही है…', ml: 'അന്വേഷിക്കുന്നു…', kn: 'ತನಿಖೆ ನಡೆಯುತ್ತಿದೆ…', ta: 'ஆராய்கிறது…' },
  'links.open': { en: 'Open through SunoSafe', hi: 'SunoSafe के ज़रिए खोलें', ml: 'SunoSafe വഴി തുറക്കുക', kn: 'SunoSafe ಮೂಲಕ ತೆರೆಯಿರಿ', ta: 'SunoSafe வழியாகத் திற' },
  'links.opening': { en: 'Checking your block list…', hi: 'आपकी ब्लॉक सूची देखी जा रही है…', ml: 'നിങ്ങളുടെ ബ്ലോക്ക് പട്ടിക പരിശോധിക്കുന്നു…', kn: 'ನಿಮ್ಮ ಬ್ಲಾಕ್ ಪಟ್ಟಿ ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ…', ta: 'உங்கள் தடைப் பட்டியலைச் சரிபார்க்கிறது…' },
  'links.paused': {
    en: 'Shield is paused. Turn it on in Settings to check links.', hi: 'सुरक्षा रुकी हुई है। लिंक जाँचने के लिए सेटिंग्स में इसे चालू करें।',
    ml: 'സംരക്ഷണം നിർത്തിവച്ചിരിക്കുന്നു. ലിങ്കുകൾ പരിശോധിക്കാൻ ക്രമീകരണങ്ങളിൽ ഓണാക്കുക.', kn: 'ರಕ್ಷಣೆ ನಿಲ್ಲಿಸಲಾಗಿದೆ. ಲಿಂಕ್ ಪರಿಶೀಲಿಸಲು ಸೆಟ್ಟಿಂಗ್‌ಗಳಲ್ಲಿ ಆನ್ ಮಾಡಿ.',
    ta: 'பாதுகாப்பு இடைநிறுத்தப்பட்டுள்ளது. இணைப்புகளைச் சரிபார்க்க அமைப்புகளில் இயக்கவும்.',
  },
  'links.blockedTitle': { en: 'SunoSafe blocked this website', hi: 'SunoSafe ने यह वेबसाइट ब्लॉक कर दी', ml: 'SunoSafe ഈ വെബ്സൈറ്റ് ബ്ലോക്ക് ചെയ്തു', kn: 'SunoSafe ಈ ವೆಬ್‌ಸೈಟ್ ಅನ್ನು ಬ್ಲಾಕ್ ಮಾಡಿದೆ', ta: 'SunoSafe இந்த இணையதளத்தைத் தடுத்தது' },
  'links.goBack': { en: 'Go back to safety', hi: 'सुरक्षित जगह पर लौटें', ml: 'സുരക്ഷിതമായി തിരികെ പോകുക', kn: 'ಸುರಕ್ಷಿತವಾಗಿ ಹಿಂತಿರುಗಿ', ta: 'பாதுகாப்பாகத் திரும்பு' },
  'links.notLink': { en: 'This is not a website link', hi: 'यह वेबसाइट का लिंक नहीं है', ml: 'ഇതൊരു വെബ്സൈറ്റ് ലിങ്ക് അല്ല', kn: 'ಇದು ವೆಬ್‌ಸೈಟ್ ಲಿಂಕ್ ಅಲ್ಲ', ta: 'இது இணையதள இணைப்பு அல்ல' },
  'links.notBlocked': { en: 'Not on your block list', hi: 'आपकी ब्लॉक सूची में नहीं है', ml: 'നിങ്ങളുടെ ബ്ലോക്ക് പട്ടികയിൽ ഇല്ല', kn: 'ನಿಮ್ಮ ಬ್ಲಾಕ್ ಪಟ್ಟಿಯಲ್ಲಿ ಇಲ್ಲ', ta: 'உங்கள் தடைப் பட்டியலில் இல்லை' },
  'links.investigateFirst': { en: 'Investigate it first (recommended)', hi: 'पहले इसकी जाँच करें (सुझाव)', ml: 'ആദ്യം അന്വേഷിക്കുക (ശുപാർശ)', kn: 'ಮೊದಲು ತನಿಖೆ ಮಾಡಿ (ಶಿಫಾರಸು)', ta: 'முதலில் ஆராயவும் (பரிந்துரை)' },
  'links.openAnyway': { en: 'Open it anyway', hi: 'फिर भी खोलें', ml: 'എന്നിട്ടും തുറക്കുക', kn: 'ಆದರೂ ತೆರೆಯಿರಿ', ta: 'இருந்தாலும் திற' },
  'links.blockedList': { en: 'Your blocked websites', hi: 'आपकी ब्लॉक की गई वेबसाइटें', ml: 'നിങ്ങൾ ബ്ലോക്ക് ചെയ്ത വെബ്സൈറ്റുകൾ', kn: 'ನೀವು ಬ್ಲಾಕ್ ಮಾಡಿದ ವೆಬ್‌ಸೈಟ್‌ಗಳು', ta: 'நீங்கள் தடுத்த இணையதளங்கள்' },
  'links.none': { en: 'Nothing blocked yet.', hi: 'अभी तक कुछ ब्लॉक नहीं हुआ।', ml: 'ഇതുവരെ ഒന്നും ബ്ലോക്ക് ചെയ്തിട്ടില്ല.', kn: 'ಇನ್ನೂ ಏನೂ ಬ್ಲಾಕ್ ಮಾಡಿಲ್ಲ.', ta: 'இதுவரை எதுவும் தடுக்கப்படவில்லை.' },
  'links.wholeSite': { en: 'Whole site: ', hi: 'पूरी साइट: ', ml: 'മുഴുവൻ സൈറ്റ്: ', kn: 'ಸಂಪೂರ್ಣ ಸೈಟ್: ', ta: 'முழுத் தளம்: ' },
  'links.howTitle': { en: 'How link protection works today', hi: 'आज लिंक सुरक्षा कैसे काम करती है', ml: 'ഇന്ന് ലിങ്ക് സംരക്ഷണം എങ്ങനെ പ്രവർത്തിക്കുന്നു', kn: 'ಇಂದು ಲಿಂಕ್ ರಕ್ಷಣೆ ಹೇಗೆ ಕೆಲಸ ಮಾಡುತ್ತದೆ', ta: 'இன்று இணைப்புப் பாதுகாப்பு எப்படிச் செயல்படுகிறது' },
  'links.howText': {
    en: 'Links you open through SunoSafe are checked against your block list first. SunoSafe cannot see links you open in other apps.',
    hi: 'SunoSafe के ज़रिए खोले गए लिंक पहले आपकी ब्लॉक सूची से मिलाए जाते हैं। दूसरे ऐप में खोले गए लिंक SunoSafe नहीं देख सकता।',
    ml: 'SunoSafe വഴി തുറക്കുന്ന ലിങ്കുകൾ ആദ്യം നിങ്ങളുടെ ബ്ലോക്ക് പട്ടികയുമായി ഒത്തുനോക്കുന്നു. മറ്റ് ആപ്പുകളിൽ തുറക്കുന്ന ലിങ്കുകൾ SunoSafe-ന് കാണാനാവില്ല.',
    kn: 'SunoSafe ಮೂಲಕ ತೆರೆಯುವ ಲಿಂಕ್‌ಗಳನ್ನು ಮೊದಲು ನಿಮ್ಮ ಬ್ಲಾಕ್ ಪಟ್ಟಿಯೊಂದಿಗೆ ಹೋಲಿಸಲಾಗುತ್ತದೆ. ಬೇರೆ ಆ್ಯಪ್‌ಗಳಲ್ಲಿ ತೆರೆಯುವ ಲಿಂಕ್‌ಗಳನ್ನು SunoSafe ನೋಡಲಾರದು.',
    ta: 'SunoSafe வழியாகத் திறக்கும் இணைப்புகள் முதலில் உங்கள் தடைப் பட்டியலுடன் ஒப்பிடப்படும். மற்ற செயலிகளில் திறக்கும் இணைப்புகளை SunoSafe பார்க்க முடியாது.',
  },
  'links.planTitle': { en: 'Catch links from every app', hi: 'हर ऐप के लिंक पकड़ना', ml: 'എല്ലാ ആപ്പുകളിലെയും ലിങ്കുകൾ പിടിക്കുക', kn: 'ಎಲ್ಲ ಆ್ಯಪ್‌ಗಳ ಲಿಂಕ್ ಹಿಡಿಯುವುದು', ta: 'எல்லாச் செயலிகளின் இணைப்புகளையும் பிடித்தல்' },
  'links.planText': {
    en: 'The Android app will be able to register as a link handler, so links tapped in other apps pass through SunoSafe.',
    hi: 'Android ऐप लिंक खोलने वाले ऐप के रूप में जुड़ सकेगा, ताकि दूसरे ऐप में दबाए गए लिंक SunoSafe से होकर जाएँ।',
    ml: 'Android ആപ്പിന് ലിങ്ക് തുറക്കുന്ന ആപ്പായി രജിസ്റ്റർ ചെയ്യാൻ കഴിയും, അങ്ങനെ മറ്റ് ആപ്പുകളിൽ തൊടുന്ന ലിങ്കുകൾ SunoSafe വഴി കടന്നുപോകും.',
    kn: 'Android ಆ್ಯಪ್ ಲಿಂಕ್ ತೆರೆಯುವ ಆ್ಯಪ್ ಆಗಿ ನೋಂದಾಯಿಸಿಕೊಳ್ಳಲು ಸಾಧ್ಯವಾಗುತ್ತದೆ, ಆಗ ಬೇರೆ ಆ್ಯಪ್‌ಗಳಲ್ಲಿ ಒತ್ತಿದ ಲಿಂಕ್‌ಗಳು SunoSafe ಮೂಲಕ ಹೋಗುತ್ತವೆ.',
    ta: 'Android செயலி இணைப்புகளைத் திறக்கும் செயலியாகப் பதிவு செய்ய முடியும்; அப்போது மற்ற செயலிகளில் தொடும் இணைப்புகள் SunoSafe வழியாகச் செல்லும்.',
  },

  // ---- link facts card
  'facts.to': { en: 'Link to: {host}', hi: 'लिंक: {host}', ml: 'ലിങ്ക്: {host}', kn: 'ಲಿಂಕ್: {host}', ta: 'இணைப்பு: {host}' },
  'facts.unknown': { en: 'unknown website', hi: 'अनजान वेबसाइट', ml: 'അജ്ഞാത വെബ്സൈറ്റ്', kn: 'ಅಪರಿಚಿತ ವೆಬ್‌ಸೈಟ್', ta: 'அறியப்படாத இணையதளம்' },
  'facts.leads': { en: 'It finally leads to:', hi: 'आख़िर में यह यहाँ ले जाता है:', ml: 'ഒടുവിൽ ഇത് എത്തുന്നത്:', kn: 'ಕೊನೆಗೆ ಇದು ಇಲ್ಲಿಗೆ ಹೋಗುತ್ತದೆ:', ta: 'இறுதியில் இது செல்லும் இடம்:' },
  'facts.none': { en: 'No warning signs were found for this link.', hi: 'इस लिंक में कोई चेतावनी संकेत नहीं मिला।', ml: 'ഈ ലിങ്കിൽ മുന്നറിയിപ്പ് അടയാളങ്ങളൊന്നും കണ്ടില്ല.', kn: 'ಈ ಲಿಂಕ್‌ನಲ್ಲಿ ಎಚ್ಚರಿಕೆ ಚಿಹ್ನೆಗಳು ಕಂಡುಬಂದಿಲ್ಲ.', ta: 'இந்த இணைப்பில் எச்சரிக்கை அறிகுறிகள் எதுவும் இல்லை.' },
  'facts.checks': { en: 'Checks run:', hi: 'की गई जाँचें:', ml: 'നടത്തിയ പരിശോധനകൾ:', kn: 'ನಡೆಸಿದ ಪರಿಶೀಲನೆಗಳು:', ta: 'நடந்த சரிபார்ப்புகள்:' },
} satisfies Record<string, Entry>;

export type Key = keyof typeof S;

export function translate(lang: Lang, key: Key, vars?: Record<string, string>): string {
  const entry: Entry = S[key];
  let text = entry[lang] ?? entry.en;
  if (vars) for (const [k, v] of Object.entries(vars)) text = text.split(`{${k}}`).join(v);
  return text;
}

const LangContext = createContext<Lang>('en');
export const LangProvider = LangContext.Provider;

export function useLang(): Lang {
  return useContext(LangContext);
}

/** `const t = useT(); t('home.checkMessage')` */
export function useT() {
  const lang = useContext(LangContext);
  return useCallback((key: Key, vars?: Record<string, string>) => translate(lang, key, vars), [lang]);
}
