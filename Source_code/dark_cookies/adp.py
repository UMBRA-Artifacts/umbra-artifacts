# Import the required Interfaces from the User Input Interface module.
from dark_cookies.uii import Checkbox_Input
from dark_cookies.id_like_checker import is_id_cookie
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from difflib import SequenceMatcher

# Import the textstat module, used for text readability metrics.
import textstat
# Import the opencv pip module, used for image processing.
import cv2
import logging
import tldextract
import sqlite3
import json
import re
import os
import logging

# Class which handles the automatic detection of Dark Patterns on the inital cookie dialog.
class Automatic_Dark_Patterns():
    def __init__(self, conf):
        # The WebDriver instance
        self.driver = conf.driver
        # The domain of the website
        self.domain = conf.domain
        # Enable to option to make the program fully automatic
        self.data_folder_name = conf.options.DATA_FOLDER_NAME 
        self.OPT_AUTO = conf.options.OPT_AUTO
        self.OPT_SAVE_COOKIES = conf.options.OPT_SAVE_COOKIES
        self.OPT_CR = conf.options.OPT_CR
        self.resultsDB = conf.resultsDB
    ############################ Added Language helper ####################################
    # --- Language helpers ---
    try:
        from langdetect import detect
    except Exception:
        detect = None
    @staticmethod
    def translate_to_english(text: str) -> str:
        """Drop in your translator here if you want (Argos/Google/DeepL).
       If no translator is available, just return the original."""
        try:
            import argostranslate.translate  # optional offline
            return argostranslate.translate.translate(text, "auto", "en")
        except Exception:
            return text
    @staticmethod
    def normalize_dialog_text(raw_text: str) -> str:
        if not raw_text:
            return ""
        lang = None
        det = getattr(Automatic_Dark_Patterns, "detect", None)
        if det:
            try:
                lang = det(raw_text)
            except Exception:
                pass
        if lang and lang != "en":
            raw_text = Automatic_Dark_Patterns.translate_to_english(raw_text) or raw_text
        return raw_text.lower()

    ##################### Laqnguage helper ends here ######################################

    def find_dps(self):
        """ Function to find the auto dark patterns, get the user to validate them and add them to the database.
        """
        logging.info("Auto Detecting DPs for '"+str(self.domain)+"'...")
        # Define the intial values of the dark patterns (as tagged by the automatically)


        # Dark pattern descriptions
        dark_patterns_desc = {#"DP0" : "No Cookie Dialog present.",
                         "DP1" : "Only Opt-in option is present on initial Cookie Dialog. (OnlyOptIn)",
                         "DP2" : "Background color of Opt-in button leads to it being highlighted more compared to Opt-out button. (HighlightedOptIn)",
                         "DP3" : "Dialog Obstructs the window. (ObstructWindow)",
                         "DP4" : "Large amount of text on cookie dialog.(ComplexText)",
                         "DP5" : "Multiple layers to a cookie dialog.(MoreOptions)",
                         "DP6" : "Ambiguous Close button (in addition to Accept button).(AmbiguousClose)",
                         "DP7" : "Multiple distinct Cookie Dialogs present on a page.(MultipleDialogs)",
                         "DP8" : "At least one Preference Slider is enabled by default.(Preference Slider)",
                         "DP9" : "Clicking Close button leads to more cookies being selected.(CloseMore Cookies)",
                         "DP10": "More cookies are set regardless of Opt-out button being clicked.",
                         "DP11": "No information about cookies on the first page (CookieInfoDisplay).",
                         "DP12": "No information about the purpose of cookies on the first page (PurposeInfoDisplay).",
                         "DP13": "Pricing based on opt-out decision. (OptOutPricing)",
                         "DP14": "Cookie consent revocation is not possible. (ConsentRevocationPossible)",
                         "DP15": "Cookie consent revocation is hard. (HardRevocation)",
                         "DP16": "Pre-consent cookie loading. (PreConsent Cookies)",
                         "DP17": "Unclear Legal Basis. ((LegalBasisAmbiguity)",
                         "DP18": "Default Rejection as Non-functional. (FakeOptOut)",
                         "DP19" : "Takes more clicks to Opt-out than Opt-in or Opt-out option is not clearly visible.(Multi-Click Opt-Out)",
                         }
        # Create a dictionart to store the dark pattern values.
        dark_patterns = {d:False for d in dark_patterns_desc}
        
        # Get clickables numbers and store them in a dictionary.
        #if self.OPT_AUTO:
            #clickables = self.resultsDB.clickables.select_clickableNum_autoType(self.domain)
        #else:
        clickables = self.resultsDB.clickables.select_clickableNum_type(self.domain)
        clickables = {c[0]:c[1] for c in clickables}
        # get the clickable types and store them in a set.
        clickables_types = set(clickables.values())
        
        # Analyse the cookie captures for ID-like cookies
        conn = sqlite3.connect(self.resultsDB.file_name)
        c = conn.cursor()
        c.execute("SELECT num_cookies FROM cookie_collections WHERE domain = :domain AND type = 'initial'", {"domain": self.domain,})
        num_intial = c.fetchall()
        if num_intial:
            _initial_domains, _initial_first_party_cookies, _initial_third_party_cookies, initial_id_like_cookies = self.check_cookies('initial')
        else:
            initial_id_like_cookies = 0
        logging.debug(f"initial_id_like_cookies {initial_id_like_cookies}")
        
        c.execute("SELECT num_cookies FROM cookie_collections WHERE domain = :domain AND type = 'opt-in option'", {"domain": self.domain,})
        num_opt_in = c.fetchall()
        if num_opt_in:
            _opt_in_domains, _opt_in_first_party_cookies, _opt_in_third_party_cookies, opt_in_id_like_cookies = self.check_cookies('opt-in option')
        else:
            opt_in_id_like_cookies = 0
        logging.debug(f"opt_in_id_like_cookies {opt_in_id_like_cookies}")
        
        c.execute("SELECT num_cookies FROM cookie_collections WHERE domain = :domain AND type = 'opt-out option'", {"domain": self.domain,})
        num_opt_out = c.fetchall()
        if num_opt_out:
            _opt_out_domains, _opt_out_first_party_cookies, _opt_out_third_party_cookies, opt_out_id_like_cookies = self.check_cookies('opt-out option')
        else:
            opt_out_id_like_cookies = 0
        logging.debug(f"opt_out_id_like_cookies {opt_out_id_like_cookies}")
        
        c.execute("SELECT num_cookies FROM cookie_collections WHERE domain = :domain AND type = 'close option'", {"domain": self.domain,})
        num_close_button = c.fetchall()
        if num_close_button:
            _close_domains, _close_first_party_cookies, _close_third_party_cookies, close_id_like_cookies = self.check_cookies('close option')
        else:
            close_id_like_cookies = 0
        logging.debug(f"close_id_like_cookies {close_id_like_cookies}")
        conn.close()  
        
        # DP 1: Only Opt-in option is present.
        # CRITERIA - Satisfies all of the following:
        # 1. There is a opt-in button present.
        # 2. There is not a more options button present.
        # 3. There is not a opt-out button present.
        if "opt-in option" in clickables_types and "more options" not in clickables_types and "opt-out option" not in clickables_types:
            dark_patterns["DP1"] = True
        
        # DP 2: Background color of Opt-in button makes it highlighted compared to Opt-out button.
        # CRITERIA: Satisfies all of the following:
        # 1. There is an opt-in option present.
        # 2. There is an opt-out option present or a more options button present.
        # 3. The opt-in button greyscale color is dark.
        # 4. The opt-out button greyscale color is light and the more options button greyscale color is light.
        if "opt-in option" in clickables_types and ("opt-out option" in clickables_types or "more options" in clickables_types):
            opt_in_num = [c for c in clickables if clickables[c] == "opt-in option"][0]
            if "opt-out option" in clickables_types:
                opt_out_num = [c for c in clickables if clickables[c] == "opt-out option"][0]
            else:
                opt_out_num = [c for c in clickables if clickables[c] == "more options"][0]
            opt_in_file_name = self.data_folder_name + "/screenshots/clickables/"+str(opt_in_num)+".png"
            opt_out_file_name = self.data_folder_name + "/screenshots/clickables/"+str(opt_out_num)+".png"
            opt_in_colour = self.check_image_greyscale(opt_in_file_name)
            opt_out_colour = self.check_image_greyscale(opt_out_file_name)
            if opt_in_colour == "dark" and opt_out_colour == "light":
                dark_patterns["DP2"] = True
         
        # DP 3: Size of dialog takes up more than 60% of the webpage.
        # CRITERIA - The area (length*width) of the dialog is greater than 60% of the area of the webpage.
        max_area = 1920 * 1080
        dialog_num = self.resultsDB.dialogs.select_dialognum_selector_where_domain_checked(self.domain, "True")[0][0]
        dialog_file_name = self.data_folder_name + "/screenshots/dialogs/"+str(dialog_num)+".png" 
        image = cv2.imread(dialog_file_name)
        dialog_dims = image.shape
        dialog_area = dialog_dims[0] * dialog_dims[1]
        area_percentage = float(dialog_area / max_area)
        if area_percentage > 0.6:
            dark_patterns["DP3"] = True
            
        # DP 4: Large amount of text on cookie dialog
        # CRITERIA - the FK score of the dialog is less than 50.
        text = self.resultsDB.dialogs.select_text(self.domain, dialog_num)
        fk_score = textstat.flesch_reading_ease(text or "")
        if fk_score < 50:
            dark_patterns["DP4"] = True
        # NEW: normalized copy for DP11/12/13/15(C1)/17 phrase matching
        dialog_text_norm = Automatic_Dark_Patterns.normalize_dialog_text(text)
        # DP 5: Multiple layers to a cookie dialog
        # CRITERIA - a more options button is present.
        if "more options" in clickables_types:
            dark_patterns["DP5"] = True
                    
        # DP 6: Ambiguous Close button present.
        # CRITERIA - a close option is present.
        if "close option" in clickables_types:
            dark_patterns["DP6"] = True
        
        # DP 7: Multiple distinct Cookie Dialogs present on a page.
        # Dialog score must be positive and dialog text must not be a substring of another dialog.
        # CRITERIA - there are more than 1 distinct candidate dialogs which means:
        # 1. The candidate dialogs being considered all have a score greater than 0.
        # 2. At least one candidate is the same as or a substring of another candidate.
        diags = self.resultsDB.dialogs.select_text_where_score(self.domain, 0.0)
        diags = {d[0]:d[1] for d in diags} 
        distinct_diags = self.find_distict(diags)
        num_distinct_diags = len(distinct_diags)
        if num_distinct_diags > 1:
            dark_patterns["DP7"] = True
        
        # DP 8: At least one Preference Slider is enabled by default.
        # CRITERIA - a preference slider is present and satifies the following:
        # 1. The preference slider is enabled (is_enabled function of this element returns True).
        # 2. The preference slider is selected (is_seleted function of this element returns True).
        if "preference slider enabled" in clickables_types:
            dark_patterns["DP8"] = True
        
        # DP 9: Clicking the close button leads to more ID-like cookies being set.
        if close_id_like_cookies > initial_id_like_cookies:
            logging.debug("DP9: Clicking Close button leads to more cookies being selected.")
            dark_patterns["DP9"] = True
            
        # DP 10: More cookies are set regardless of the Opt-out button being clicked.
        if opt_out_id_like_cookies > initial_id_like_cookies:
            logging.debug("DP10: More cookies are set regardless of Opt-out button being clicked.")
            dark_patterns["DP10"] = True 

        # ---- DP11  :  CookieInfoDisplay -------------------------
        dialog_text = dialog_text_norm
        COOKIE_DEFINITION_PHRASES = [
            "cookies are small text files",
            "cookies are small files",
            "cookies (small text files",
            "cookies contain",
            "cookies hold",
            "cookies identify",
            "cookies track",
            "Cookies and other tools store or retrieve personal data",
            "script (e.g. cookies)",
            "script such as cookies",
            "small files called cookies",
            "A cookie is a small text file",
            
]
        # If none of the definitions appear, it's a DP11
        if not any(phrase in dialog_text for phrase in COOKIE_DEFINITION_PHRASES):
            dark_patterns["DP11"] = True
# ---------------------------------------------------------
        # ---- DP12 : PurposeInfoDisplay -------------------------
        dialog_text = dialog_text_norm
        COOKIE_PURPOSE_PHRASES = [
            "for analytics",  # For tracking website usage and performance.
            "to personalize content",  # For providing content based on user preferences.
            "to improve user experience",  # Enhancing the website's usability.
            "for marketing",  # For serving personalized ads.
            "to track usage",  # For tracking behavior across sessions or pages.
            "for advertising",  # For showing targeted ads.
            "for functional purposes",  # For essential features like keeping users logged in.
            "to remember your preferences",  # For storing preferences like language or theme.
            "to deliver targeted ads",  # For ads based on browsing history.
            "to optimize our website",  # For improving the performance of the site.
            "to provide social media features",  # Cookies for enabling social media sharing.
            "for site security",  # For security-related cookies like preventing fraud.
            "to gather demographic information",  # For collecting data on user groups.
            "to provide content recommendations",  # For suggesting content to users based on their behavior.
            "to improve site performance",  # For optimizing the load time and response time.
            "for user authentication",  # Cookies that store login session data.
            "for site functionality",  # For making sure the site works properly.
            "for managing your shopping cart",  # For e-commerce websites that track your cart.
            "for better site navigation",  # For improving navigation based on user behavior.
            "to facilitate payment processing",  # For handling cookies on payment gateways.
            "to maintain session state",  # For keeping the user session active.
            "for geo-targeting",  # Cookies for providing location-based services or content.
            "to enable website features",  # To activate features like search bars or filters.
            "to support customer support",  # For cookies enabling customer service features.
            "for monitoring site performance",  # For checking the health of the website's features.
            "to analyze website traffic",  # Cookies for tracking how users arrive at and navigate websites.
            "to track affiliate links",  # For tracking referrals through affiliate links.
            "to enhance site content",  # For tailoring content based on previous interactions.
            "for A/B testing",  # Cookies used for split testing different versions of the site.
            "to analyze user behavior",  # For understanding how users interact with the site.
            "to enable features like chat",  # For live chat features powered by cookies.
            "for improving ads efficiency",  # For enhancing how ads are displayed based on user interaction.
            "for better targeting",  # For refining how ads are shown based on browsing activity.
            "for personalization",  # For making website interactions tailored to the individual.
            "to provide you with the best experience",  # General purpose cookies.
            "for collecting statistical data",  # Cookies used for analyzing data like page views.
            "for retargeting",  # For serving ads to users based on their previous interactions.
            "to assess the performance of ads",  # Cookies for measuring ad effectiveness.
            "for affiliate marketing",  # Cookies to track sales generated from affiliate programs.
            "to recommend products",  # For suggesting products or services based on user preferences.
            "for customizing advertisements",  # For showing customized ads based on browsing history.
            "to deliver and enhance the quality of services",  # New phrase
            "to analyze traffic", "creating custom content profile", # New phrase
            "to serve advertising", "remember your settings", # New phrase
            "for session management", "personalization of communication",  # To keep the session active
            "to tailor content and ads", "store and access information", # Another variation
            "to improve your experience", "Authentication and security", "third party advertising purposes",
            "to help improve your experience", "to process device information",
            "proper operation of the website", # New addition for collecting data
            "remember their preferences", # New addition for analyzing data
            "profiling", # New addition for profiling users
            "to access personal data for analytics", # New addition for monitoring user behavior
            "to access personal data for advertising",
            "to access personal data for social engineering","relevant personalized advertisements","process personal data", "interest-based advertising",
            "cookies save your preferences", "cookies help websites remember","cookies allow websites","to show relevant ads", "improve site functionality",
            "optimizing", "to enhance", "personalized advertising", "personalize our site", "measure site performance", "analyse site traffic", "analze our traffic",
            "to deliver and enhance the quality of services", "to analyze traffic","for statistical purposes", "for measuring performance",
            "performance cookies", "functionality cookies", "advertising cookies"
            ]
        key_terms = [
            ("enhance", "site"),  # e.g., "to enhance site content"
            ("enhance", "website"),  # e.g., "to enhance the website"
            ("enhance", "performance"),  # e.g., "to enhance website performance"
    
                # For "analytics" related purposes
            ("track", "usage"),  # e.g., "to track usage"
            ("analyze", "data"),  # e.g., "to analyze data"
            ("monitor", "activity"),  # e.g., "to monitor activity"
    
            # For "advertising" and "targeting" related purposes
            ("target", "ads"),  # e.g., "to target ads"
            ("serve", "ads"),  # e.g., "to serve ads"
            ("personalize", "advertising"),  # e.g., "to personalize advertising"
    
            # For "user preferences" related purposes
            ("remember", "preferences"),  # e.g., "to remember preferences"
            ("store", "preferences"),  # e.g., "to store preferences"
    
            # For "functional purposes" related purposes
            ("maintain", "session"),  # e.g., "to maintain session state"
            ("ensure", "functionality"),  # e.g., "to ensure functionality"
    
            # For "content recommendations" related purposes
            ("recommend", "content"),  # e.g., "to recommend content"
            ("suggest", "content"),  # e.g., "to suggest content"
    
            # For "social media" related purposes
            ("enable", "social media"),  # e.g., "to enable social media sharing"
            ("allow", "social media"),  # e.g., "to allow social media features"
    
            # For "geo-targeting" related purposes
            ("geo", "targeting"),  # e.g., "for geo-targeting"
            ("location", "based services"),  # e.g., "location-based services"
    
            # For "A/B testing" related purposes
            ("perform", "A/B testing"),  # e.g., "to perform A/B testing"
            ("conduct", "A/B tests"),  # e.g., "to conduct A/B tests"
    
            # For "session management" related purposes
            ("manage", "session"),  # e.g., "to manage session"
            ("keep", "session active"),  # e.g., "to keep session active"
    
             # For "improving experience" related purposes
            ("improve", "user experience"),  # e.g., "to improve user experience"
            ("optimize", "experience")  # e.g., "to optimize experience"
            ]
        has_purpose_phrase = any(phrase in dialog_text for phrase in COOKIE_PURPOSE_PHRASES)

# Only check fuzzy match if no exact match is found
        has_fuzzy_match = False
        if not has_purpose_phrase:
            has_fuzzy_match = Automatic_Dark_Patterns.match_keywords(dialog_text, key_terms)

# DP12 flag logic
        if not has_purpose_phrase and not has_fuzzy_match:
            dark_patterns["DP12"] = True
        else:
            dark_patterns["DP12"] = False

# ---------------------------------------------------------
            # ---- DP15 helper: upfront "withdraw any time" disclosure on first page ----
        WITHDRAWAL_DISCLOSURE_PHRASES = [
            "withdraw your consent", "withdraw consent", "revoke your consent", "revoke consent",
            "change your consent", "change your preferences at any time",
            "you can change your cookie settings at any time",
            "you may withdraw your consent at any time", "right to withdraw consent",
            "modify your consent", "adjust your consent", "choice of consent"
        ]
        informs_withdrawal_on_banner = any(p in dialog_text_norm for p in WITHDRAWAL_DISCLOSURE_PHRASES)

        # DP13: Pricing based on opt-out decision
        PAY = r"(subscribe|subscription|pay|price|pricing|€|\$|£|₹|kr|zł|per\s*(month|week|year)|trial|ad[- ]?free|premium)"
        CONSENT = r"(cookie|cookies|consent|tracking|reject|refuse|deny|opt[- ]?out|without\s+(ads?|tracking|advertising)|ad[- ]?free|with\s+(ads?|tracking)|purchase)"


        # proximity both ways within 80 chars
        PATTERN = re.compile(
            rf"{PAY}.{{0,200}}{CONSENT}|{CONSENT}.{{0,200}}{PAY}",
            flags=re.I
        )
        
        if PATTERN.search(dialog_text_norm):
           dark_patterns["DP13"] = True


        # Otherwise, not DP13
        else:
            dark_patterns["DP13"] = False     
        ################################################################################
        ###############################################################################################################
 # DP18: Default Rejection as Non-functional. (FakeOptOut)
        # DP18: Default Rejection as Non-functional (Fake Opt-Out)
# Optional stricter check
        if not hasattr(self, "OPT_DP18_STRICT"):
            self.OPT_DP18_STRICT = False  # default False

        _opt_out_first_party_cookies = 0
        _opt_out_third_party_cookies = 0

        # Default: get cookies after clicking Reject button
        reject_id_like_cookies = opt_out_id_like_cookies  # from existing collection
        reject_first_party_cookies = _opt_out_first_party_cookies
        reject_third_party_cookies = _opt_out_third_party_cookies

        if self.OPT_DP18_STRICT:
    # Strict: include first-party and ID-like cookies
            total_reject_cookies = reject_first_party_cookies + reject_third_party_cookies + reject_id_like_cookies
        else:
    # Standard: only third-party and ID-like cookies
            total_reject_cookies = reject_third_party_cookies + reject_id_like_cookies

        if total_reject_cookies > 0:
            dark_patterns["DP18"] = True
            logging.info(f"DP18: Reject button failed, {total_reject_cookies} cookies still set after rejection.")
            post_reject_cookies = self.get_cookie_details('opt-out option') 
            domain = self.domain  # or any other unique identifier for the URL
            self.save_cookie_details(post_reject_cookies, f"dp18_postreject_{domain}.json")
        else:
            dark_patterns["DP18"] = False
            logging.info("DP18: Reject button successfully blocked cookies.")
        self.save_results_to_json(dark_patterns, filename="dp18_results.json")

###############################################################################################################
        # "DP19" : "Takes more clicks to Opt-out than Opt-in or Opt-out option is not clearly visible.(MultiClickOptOut)",
        # [Add DP19 logic here later]
# Check if "Reject All" or "Reject" is available in the clickables
        REJECT_BUTTON_KEYWORDS = [
            "reject all", "reject", "i do not accept", "deny", "deny all", 
            "decline", "decline all", "refuse", "refuse all", "optout", 
            "disallow all", "No thanks", "opt-out", "withdraw consent", 
            "revoke consent", "decline cookies", "reject cookies"
]
        dialog_text = Automatic_Dark_Patterns.normalize_dialog_text(text)
# Check if any of the reject button phrases appear in the dialog text
        reject_button_present = any(
            keyword in dialog_text for keyword in REJECT_BUTTON_KEYWORDS
        )

# If any reject-related keyword is found in the dialog text, we consider DP19 as False
        if reject_button_present:
            dark_patterns["DP19"] = False
            logging.info(f"DP19: Reject button detected in dialog text, setting DP19 as False.")
        else:
    # DP19 will be triggered if:
    # 1. Neither "more options" nor "opt-out option" is present,
    # 2. Or if "opt-in" is present and more than 1 click is required.
            if ("more options" not in clickables_types and "opt-out option" not in clickables_types) or ("opt-in option" in clickables_types and num_clicks > 1):
                dark_patterns["DP19"] = True
                logging.info(f"DP19: Reject button not found, hence setting DP19 as True.")
            else:
                dark_patterns["DP19"] = False
                logging.info(f"DP19: Setting DP19 as False.")

            
################################################################################################################

        ##################### Added this ##############################
        # ----- DP14 / DP15: Consent revocation availability & difficulty -----
        if self.driver is None:
            logging.error("WebDriver is None! Cannot proceed with consent revocation check.")
        else:
            dp14_15 = self.check_consent_revocation()
            dark_patterns["DP14"] = dp14_15.get("DP14", True)
            logging.debug("Setting DP14 to %s", dp14_15.get("DP14"))

            try:
                dialog_text_norm = Automatic_Dark_Patterns.normalize_dialog_text(
                    self.resultsDB.dialogs.select_text(self.domain, dialog_num)
                )
                REVOCATION_TEXTUAL_PHRASES = [
                    "at any time",
                    "withdraw",
                    "revoke",
                    "footer",
                    "change your consent",
                    "can be changed",
                    "change your preferences",
                    "may be withdrawn",
                    "adjust your preferences",
                    "bottom of each page"  # optional heuristic
                ]
                if any(p in dialog_text_norm for p in REVOCATION_TEXTUAL_PHRASES):
                    logging.info("DP14 override: textual indication of revocation found.")
                    dark_patterns["DP14"] = False
            except Exception as e:
                logging.warning(f"DP14 textual override failed: {e}")
            # ----- New DP15 combination (C1–C4) without changing DP14 -----
# C2 from your finder: reuse the min steps heuristic
            try:
                candidates = self._find_revocation_elements(
                    keywords=[
                    "cookie settings", "change preferences", "privacy settings", "consent management", "cookie management", "privacy preferences","consent management",
                    "manage cookies",  "revoke consent", "Privacy settings", "Revocation Tracking and Cookies","Your Privacy Choices","Your Ads Privacy Choices",
                    "change privacy settings", "access the cookie policy", "cookie policy/settings","Gestion cookies","Gérer mes cookies ",
                    "adjust consent", "withdraw consent", "do not sell my data", "do not sell my personal information","consent cookie", "cookie consent", "manage my cookies",
                    ################### Other langage helper ###############
                    "Paramètres des cookies", "Préférences des cookies", "Gérer les cookies", "Paramètres de confidentialité","Configuración de cookies",
                    "Preferencias de cookies","Gestionar cookies","Configuración de privacidad","Impostazioni dei cookie", "Preferenze dei cookie", "Gestire i cookie",
                    "Impostazioni sulla privacy", "Cookie-instellingen", "Cookievoorkeuren", "Cookies beheren", "Privacy-instellingen", "Configurações de cookies", "Preferências de cookies", 
                    "Gerenciar cookies", "Configurações de privacidade","Ρυθμίσεις cookie", "Προτιμήσεις cookie","Διαχείριση cookie", "Ρυθμίσεις απορρήτου", "Ustawienia plików cookie",
                    "Preferencje plików cookie", "Zarządzaj plikami cookie", "Ustawienia prywatności", "Cookie-inställningar", "Cookies preferenser", "Hantera cookies", "Sekretessinställningar",
                    "Evästeasetukset", "Evästeiden asetukset", "Hallitse evästeitä", "Tietosuoja-asetukset", "Informasjonskapselinnstillinger", "Informasjonskapselpreferanser", "Administrer informasjonskapsler",
                    "Personverninnstillinger", "Nastavení cookies", "Předvolby cookies", "Spravovat cookies", "Nastavení ochrany osobních údajů","Настройки cookies","Предпочтения cookies", "Управление cookies"
                    "Настройки конфиденциальности","Cookie-Präferenzen","Datenschutzeinstellungen","Cookies verwalten","Hantera cookies","Cookies verwalten","Inställningar för cookies",
                    "Opzioni dei cookie","Hantera cookies manuellt","Zustimmungsverwaltung","Cookie di consenso","Dina annonsinställningar för integritet","Impostazione dei cookie","Acceder a la política de cookies",
                    "Cookie- und Datenschutzeinstellungen anpassen","Choix de consentement","Preferenze dei cookie","Gestion des cookies", "Gérer mes cookies","Modifier les paramètres de confidentialité"
                    ################# Other lang helper #####################
                    ],
                    left_only=True
                )
            except Exception as _e:
                candidates = []

            if not candidates:
                c2_hard = False
            else:
                c2_hard = (min(c.get("steps", 3) for c in candidates) > 2)

# C3: actively click a candidate and count interactions to complete withdrawal/save
            try:
                active_steps = self._active_withdraw_clickthrough(candidates)  # defined below
            except Exception as _e:
                active_steps = 0
            c3_hard = (active_steps > 2) if active_steps > 0 else False

# C4: asymmetry vs giving consent (reuse your existing metric)
            c4_hard = False
            try:
                consent_clicks = self.resultsDB.dark_patterns.select_numClicks(self.domain)
                if isinstance(consent_clicks, (int, float)) and consent_clicks > 0 and active_steps > 0:
                    c4_hard = (active_steps > consent_clicks)
            except Exception:
                pass

# C1 was computed earlier from the banner text
            c1_hard = (not informs_withdrawal_on_banner)

# Combine: DP15 is True if any C1–C4 triggers
            dark_patterns["DP15"] = c1_hard or c2_hard or c3_hard or c4_hard
            # Enforce mutual exclusivity: if revocation isn't possible, it can't be "hard"
            if dark_patterns["DP14"]:
                dark_patterns["DP15"] = "N/A"
        ####################### Added this ############################# 
        # DP16: Pre-consent cookie loading. (PreConsent Cookies)
       ####################### Added this ############################# 
# DP16: Pre-consent cookie loading. (PreConsent Cookies)
# Optional stricter check flag (can be added to your conf.options)
        if not hasattr(self, "OPT_DP16_STRICT"):
            self.OPT_DP16_STRICT = False  # default is False

# Total cookies before consent
        pre_consent_third_party_cookies = _initial_third_party_cookies
        pre_consent_first_party_cookies = _initial_first_party_cookies
        pre_consent_id_like_cookies = initial_id_like_cookies

# Determine which cookies to check based on strict mode
        if self.OPT_DP16_STRICT:
    # Strict: any pre-consent cookies, including first-party ID-like
            total_pre_consent_cookies = pre_consent_third_party_cookies + pre_consent_id_like_cookies
            logging.debug(f"DP16 STRICT: Third-party cookies: {pre_consent_third_party_cookies}, ID-like cookies: {pre_consent_id_like_cookies}")
        else:
    # Standard: only third-party cookies
            total_pre_consent_cookies = pre_consent_third_party_cookies
            logging.debug(f"DP16 STANDARD: Third-party cookies: {pre_consent_third_party_cookies}")

# Flag DP16 if any pre-consent cookies are detected
        if total_pre_consent_cookies > 0:
            dark_patterns["DP16"] = True
            logging.info(f"DP16: Pre-consent cookie loading detected ({total_pre_consent_cookies} cookies set before consent).")
            pre_consent_cookies = self.get_cookie_details('initial')  # Get cookies before consent
            domain = self.domain  # or any other unique identifier for the URL
            self.save_cookie_details(pre_consent_cookies, f"dp16_preconsent_{domain}.json")
        else:
            dark_patterns["DP16"] = False
            logging.info("DP16: No pre-consent cookies detected.")
        

                    # ===== DP17: Unclear Legal Basis (LegalBasisAmbiguity) =====
        try:
            dp17_flag, _ = self._check_dp17(dialog_num, clickables_types, clickables)
            dark_patterns["DP17"] = dp17_flag
        except Exception as e:
            logging.warning(f"DP17 check failed: {e}")
            dark_patterns["DP17"] = False

        # Save each dark pattern to the database
        for dp in dark_patterns:
            self.resultsDB.dark_patterns.insert_into(self.domain, dp, "unconfirmed", str(dark_patterns[dp]))
        if not self.OPT_AUTO:
            self.manual_validation(dark_patterns, dark_patterns_desc)

     # DP17: Unclear Legal Basis / LegalBasisAmbiguity
        # The banner must mention a GDPR-accepted legal basis (e.g., "consent", "legitimate interest", etc.)
# ===== DP17: Unclear Legal Basis (LegalBasisAmbiguity) =====
# Does not affect other DP logic.

    def _check_dp17(self, dialog_num, clickables_types, clickables):
    # --- First page text ---
            first_txt = self.resultsDB.dialogs.select_text(self.domain, dialog_num) or ""
            first_norm = Automatic_Dark_Patterns.normalize_dialog_text(first_txt)

    # --- Try to get second-layer text if "more options" is available ---
            second_norm = ""
            if self.driver and any(
                hint in " ".join(clickables_types).lower()
                for hint in ["options", "settings", "preferences", "manage", "more options","customise", "customize", "learn", "read", "goals", "view", "adjust", "ADVANCED SETTINGS", "advanced settings"]
            ):
                logging.basicConfig(level=logging.DEBUG)
                logging.info(f"Clickables for DP17 on {self.domain}: {clickables_types}")
                logging.debug(f"Clickables details: {clickables}")
                logging.info("Second-layer options found, attempting to click...")
                try:
                    self.driver.switch_to.default_content()

                # Candidate labels for opening the second layer
                    SECOND_LAYER_TERMS = [
                    "more options", "settings", "preferences", "manage cookies",
                    "cookie settings", "customise", "customize", "learn more",
                    "read more", "show goals", "view cookies", "adjust",
                    "other options", "Data Protection Policy", "Cookie Statement", "Cookie Notice", "Privacy Notice", "Privacy and Cookie Poliocy",
                    "Cookie Disclaimer", "Configure","Privacy policy", "advanced settings", "change my cookie settings", "edit settings", "About cookies and personal data",
                    "manage preferences", "more information", "set preferences"
                    ]

                # Build case-insensitive OR clause for text matches
                    clauses = [
                        f"contains(translate(normalize-space(.), "
                        f"'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), "
                        f"'{term.lower()}')"
                        for term in SECOND_LAYER_TERMS
                    ]

                    xpath_expr = (
                        "//*[self::button or self::a or self::div or self::span]"
                        f"[{' or '.join(clauses)}]"
                    )

                    # Try all matches; take the first that yields visible second-layer text
                    for el in self.driver.find_elements(By.XPATH, xpath_expr):
                        try:
                            if not el.is_displayed():
                                continue
                            el.click()
                            WebDriverWait(self.driver, 3).until(lambda d: True)

                    # Grab visible content from common CMP containers
                            nodes = self.driver.find_elements(
                                By.XPATH,
                                "//*[contains(@role,'dialog') or contains(@class,'modal') or "
                                "contains(@class,'cmp') or contains(@id,'cmp') or "
                                "contains(@class,'consent') or contains(@id,'consent')]"
                            )
                            raw = " ".join([n.text for n in nodes if n and n.is_displayed()])[:5000]
                            second_norm = Automatic_Dark_Patterns.normalize_dialog_text(raw)
                            if second_norm:
                                break
                        except Exception:
                            continue
                except Exception:
                        pass

    # --- Legal basis keywords (synonyms included for translation variations) ---
            LEGAL_BASIS_TERMS = [t.lower() for t in [
                "GDPR Article 6", 
                "legitimate interest (GDPR)", 
                "contract performance for cookies", "legitimate interest (data protection regulation)",
                "cookie processing under GDPR", "ccpa consent","edpb guidelines",
                "processing based on consent", "GDPR", "gdpr", "edpb", "EDPB", "eprivacy",
                "cookie tracking consent", "gdpr", "article 6", "article", "ccpa", "legal basis for cookies", "legitimate interest (gdpr)", "consent to cookie use",
                "data processing consent under GDPR", "CCPA", "California Consumer Privacy Act (CCPA)", "article 7", "Article 6 (1)", 
                "CCPA consent", "GDPR Article 6 (1)(a)", "california notice at collection", "Addiotional disclosures for california residents",
                "Consent to Cookie Use (GDPR)", "ePrivacy Regulation", "ePrivacy compliant", "EDPB Guidelines", "EDPB Recommendations","European Data Protection Board"
                ]]

    # --- Does banner talk about processing/consent? ---
            ACTIVITY_TERMS = [
               "process personal data", "collect personal data", "track personal data", "use personal data", "store personal data", 
                "access personal data", "retrieve personal data", "share personal data", "transfer personal data", "analyze personal data", 
                "manage personal data", "process cookies", "track cookies", "store cookies", "track user behavior", "personalize content", 
                "serve personalized ads", "advertise products", "recommend products", "measure website usage", "analyze traffic", 
                "monitor traffic", "optimize user experience", "monitor website performance", "content personalization", "geo-targeting", 
                "personalized content", "tracking technologies", " user tracking",
                "user profiling", "process your data", "targeted advertising profiling",
                "process user's data", "advertising profiling", "consumer profiling", "behavioral targeting"
            ]
            mentions_processing = any(t in first_norm for t in ACTIVITY_TERMS) or any(t in second_norm for t in ACTIVITY_TERMS)
            mentions_legal_basis = any(t in first_norm for t in LEGAL_BASIS_TERMS) or any(t in second_norm for t in LEGAL_BASIS_TERMS)

            dp17_flag = (mentions_processing and not mentions_legal_basis)
            logging.debug(f"mentions_processing: {mentions_processing}")
            logging.debug(f"mentions_legal_basis: {mentions_legal_basis}")
            logging.debug(f"dp17_flag: {dp17_flag}")
    # --- Decision ---
            return dp17_flag, {
            "first_page": first_norm,
            "second_page": second_norm,
            "mentions_processing": mentions_processing,
            "mentions_legal_basis": mentions_legal_basis
        }
    


    ################################################# Added this #########################
    def check_consent_revocation(self):
        """
        DP14: True  -> revocation NOT possible (no control found)
            False -> revocation possible (control found somewhere)
        DP15: True  -> revocation is hard (> 2 steps heuristically)
            False -> revocation is easy (<= 2 steps)
        """
        from selenium.webdriver.support.ui import WebDriverWait
        WebDriverWait(self.driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
         )    
    # 1) Canonical keywords (lowercased)
        keywords = [
                # English
            "cookie settings","privacy settings","consent settings","consent management","Adjust cookie and privacy settings",
            "manage cookies","manage consent","manage preferences","privacy center","Your Privacy Choices","consent management",
            "privacy choices","revoke consent","withdraw consent","Manage my privacy settings","settings for cookies","cookie options",
            "withdrawal of consent","revocation","revocation tracking","opt out","opt-out", "Revocation Tracking and Cookies","Gestion cookies",
            "tracking settings","Choice of consent", "configure","set choices","do not sell my data", "do not sell my personal information","Gérer mes cookies ",
            ################### Other langage helper ###############
            "Paramètres des cookies", "Préférences des cookies", "Gérer les cookies", "Paramètres de confidentialité","Configuración de cookies",
            "Preferencias de cookies","Gestionar cookies","Configuración de privacidad","Impostazioni dei cookie", "Preferenze dei cookie", "Gestire i cookie",
            "Impostazioni sulla privacy", "Cookie-instellingen", "Cookievoorkeuren", "Cookies beheren", "Privacy-instellingen", "Configurações de cookies", "Preferências de cookies", 
            "Gerenciar cookies", "Configurações de privacidade","Ρυθμίσεις cookie", "Προτιμήσεις cookie","Διαχείριση cookie", "Ρυθμίσεις απορρήτου", "Ustawienia plików cookie",
            "Preferencje plików cookie", "Zarządzaj plikami cookie", "Ustawienia prywatności", "Cookie-inställningar", "Cookies preferenser", "Hantera cookies", "Sekretessinställningar",
            "Evästeasetukset", "Evästeiden asetukset", "Hallitse evästeitä", "Tietosuoja-asetukset", "Informasjonskapselinnstillinger", "Informasjonskapselpreferanser", "Administrer informasjonskapsler",
            "Personverninnstillinger", "Nastavení cookies", "Předvolby cookies", "Spravovat cookies", "Nastavení ochrany osobních údajů","Настройки cookies","Предпочтения cookies", "Управление cookies"
            "Настройки конфиденциальности","Cookie-Präferenzen","Datenschutzeinstellungen","Cookies verwalten","Hantera cookies","Cookies verwalten","Inställningar för cookies",
            "Opzioni dei cookie","Hantera cookies manuellt","Zustimmungsverwaltung","Cookie di consenso","Dina annonsinställningar för integritet","Impostazione dei cookie",
            "Cookie- und Datenschutzeinstellungen anpassen","Choix de consentement","Preferenze dei cookie","Gestion des cookies",
                    ################# Other lang helper #####################
            # German (helps on BILD and friends)
            "widerruf","einwilligung widerrufen","einwilligung ändern",
            "cookie-einstellungen","datenschutz-einstellungen","privatsphäre",
            "einwilligung verwalten","zustimmung verwalten","datenschutzzentrum"
    ]

        try:
        # Collect candidate revocation elements from main doc + iframes
            candidates = self._find_revocation_elements(keywords, left_only=True)

            if not candidates:
                logging.info("DP14: No revocation keywords/elements found -> revocation NOT possible.")
                return {"DP14": True, "DP15": False}

        # We found at least one element that looks like revocation
        # Heuristic 'step count' (no clicking to avoid changing site state):
        #  - step = 1 if visible & clickable now
        #  - step = 2 if present but offscreen/hidden (scroll required / in footer)
        #  - step = 3 if inside iframe or requires menu toggle (we mark as >2)
            min_steps = min(c["steps"] for c in candidates)
            for candidate in candidates:
                matched_keywords = [kw for kw in keywords if kw in candidate['we'].text.lower()]
                if matched_keywords:
                    logging.info("DP14: Revocation control found and hence DP14 setting to false.")
                    return {"DP14": False}  # Matched, so revocation is possible
            if min_steps > 2:
                logging.info("DP15: Revocation exists.")
                return {"DP14": False, "DP15": True}
            else:
                logging.info("Revocation exists, candidate found")
                return {"DP15": False}

        except Exception as exc:
             logging.warning("adp::check_consent_revocation failed: %s", exc)
        # Fail-safe: don't accuse site of no-revocation on scraper failure
        return {"DP14": False, "DP15": False}

    def _find_revocation_elements(self, keywords, left_only=True):
        """
        Find consent-revocation controls via:
        (A) KEYWORDS in text/aria-label/title (buttons/links/div/span)
        (B) ICON/BADGE heuristic near bottom-left (or bottom-left/right if left_only=False)
        Searches main document + iframes.

        Returns: list of dicts:
        {'we': WebElement, 'context': 'main'|'iframe', 'steps': int}
        """
        driver = self.driver
        results = []

    # ---------- (A) KEYWORD XPATH ----------
    # Helper: build case-insensitive XPath contains() by lowercasing via translate()
# Case-insensitive contains: lower both sides
        def ci_contains(attr_or_text, term):
            return (
        "contains("
        "translate(" + attr_or_text + ", 'ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜß', 'abcdefghijklmnopqrstuvwxyzäöüß'), "
        "'" + term.lower() + "'"  # <-- ensure needle is lower-case
        ")"
    )

        def build_xpath_for_keywords(kw_list):
            textish = []
            hrefish = []
            for kw in kw_list:
                textish.extend([
                ci_contains("normalize-space(.)", kw),
                ci_contains("@aria-label", kw),
                ci_contains("@title", kw),
        ])
                hrefish.append(ci_contains("@href", kw))   # <-- also scan href
            or_text = " or ".join(textish)
            or_href = " or ".join(hrefish)
            return (
        f"//*[(self::button or self::a or self::div or self::span or self::li)"
        f" and ( {or_text} or {or_href} )]"
    )       

        xpath = build_xpath_for_keywords(keywords)

        def scan_keywords_in_current_context(ctx):
            found = []
            try:
                elems = driver.find_elements(By.XPATH, xpath)
            except WebDriverException:
                elems = []
            for el in elems:
                steps = 1
                try:
                    if not el.is_displayed():
                        steps = 2
                except StaleElementReferenceException:
                    steps = 2
                found.append({"we": el, "context": ctx, "steps": steps})
            return found

        # ---------- (B) ICON/BADGE HEURISTIC (JS) ----------
        # words we might see in aria-label/title/class/id/attrs around cookie badges
        icon_kw = [
            "cookie", "cookies", "consent", "privacy", "settings", "preferences",
            "gdpr", "cmp", "your choices", "onetrust", "didomi", "sourcepoint",
            "iubenda", "trustarc", "manage", "choice"
        ]

        ICON_JS = r"""
        const K = JSON.parse(arguments[0]);
        const leftOnly = arguments[1];

        const hasKw = (s) => {
        if (!s) return false;
        const t = s.toLowerCase();
        return K.some(k => t.includes(k));
        };

        const out = [];
        const els = Array.from(document.querySelectorAll('button,a,div,span'));
        const vw = window.innerWidth, vh = window.innerHeight;

        for (const el of els) {
            try {
                const cs = getComputedStyle(el);
                if (cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0' || cs.pointerEvents === 'none') continue;

            const rect = el.getBoundingClientRect();
            const w = rect.width, h = rect.height;
            if (!w || !h) continue;

            // badge-ish size (heuristic)
            if (w < 24 || w > 140 || h < 24 || h > 140) continue;

            const nearBottom = (vh - rect.bottom) <= Math.max(0.05*vh, 80);
            const nearLeft   = rect.left <= Math.max(0.05*vw, 60);
            const nearRight  = (vw - rect.right) <= Math.max(0.05*vw, 60);
            const nearEdge   = leftOnly ? (nearBottom && nearLeft) : (nearBottom && (nearLeft || nearRight));
            if (!nearEdge) continue;

            const label = (el.getAttribute('aria-label')||'') + ' ' +
                          (el.getAttribute('title')||'') + ' ' +
                          (el.innerText||'');
            const id   = el.id || '';
            const cls  = (el.className && typeof el.className === 'string')
                        ? el.className
                     : (el.classList ? Array.from(el.classList).join(' ') : '');
            const attrs = (el.getAttributeNames ? el.getAttributeNames().map(n => n + ':' + (el.getAttribute(n)||'')).join(' ') : '');

            const keywordish = hasKw(label) || hasKw(id) || hasKw(cls) || hasKw(attrs);

            // circular/rounded hint
            const brTL = parseFloat(cs.borderTopLeftRadius) || 0;
            const brTR = parseFloat(cs.borderTopRightRadius) || 0;
            const brBL = parseFloat(cs.borderBottomLeftRadius) || 0;
            const brBR = parseFloat(cs.borderBottomRightRadius) || 0;
            const r = Math.min(w,h)/2;
            const circularish = Math.max(brTL,brTR,brBL,brBR) >= 0.4*r;

            if (keywordish || circularish) {
            out.push(el);
            }
        } catch(e) {}
        }
           return out;
        """

        def scan_icons_in_current_context(ctx):
            try:
                elems = driver.execute_script(ICON_JS, json.dumps(icon_kw), bool(left_only))
            except Exception:
                elems = []
            found = []
            for el in elems:
                steps = 1
                try:
                    if not el.is_displayed():
                        steps = 2
                except StaleElementReferenceException:
                    steps = 2
                found.append({"we": el, "context": ctx, "steps": steps})
            return found

    # ---------- MAIN DOC ----------
        try:
            driver.switch_to.default_content()
            results.extend(scan_keywords_in_current_context("main"))
            results.extend(scan_icons_in_current_context("main"))
        except WebDriverException:
            pass

    # ---------- IFRAMES ----------
        try:
            frames = driver.find_elements(By.TAG_NAME, "iframe")
        except Exception:
            frames = []

        for fr in frames:
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(fr)

            # keyword hits inside iframe
                for c in scan_keywords_in_current_context("iframe"):
                    c["steps"] = max(c.get("steps", 1), 3)  # context switch/menu
                    results.append(c)

            # icon hits inside iframe
                for c in scan_icons_in_current_context("iframe"):
                    c["steps"] = max(c.get("steps", 1), 3)
                    results.append(c)

            except (NoSuchElementException, WebDriverException):
                continue
            finally:
                driver.switch_to.default_content()

        return results

    def count_steps_to_revoke_consent(self):
        ...
        return 3

    def _active_withdraw_clickthrough(self, candidates):
        """
        Click a 'cookie settings / withdraw consent' entry point and count
        the number of interactions until withdrawal is completed/saved.
        """
        driver = self.driver
        steps = 0
        def cand_key(c):
            base = c.get("steps", 3)
            if c.get("context") == "main":
                base -= 0.25
            return base
        for c in sorted(candidates, key=cand_key):
            we = c.get("we")
            if not we:
                continue
            try:
                driver.switch_to.default_content()
                we.click()
                steps += 1
                BUTTON_XPATH = (
                    "//*[self::button or self::a or self::div or self::span]"
                    "[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'reject all')"
                    " or contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'deny all')"
                    " or contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'withdraw')"
                    " or contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'opt out')]"
                )
                try:
                    btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, BUTTON_XPATH))
                    )
                    btn.click()
                    steps += 1
                except Exception:
                    MASTER_TOGGLE_XPATH = (
                        "//input[@type='checkbox' or @role='switch' or @type='switch' or @aria-checked]"
                    )
                    toggles = driver.find_elements(By.XPATH, MASTER_TOGGLE_XPATH)
                    for t in toggles:
                        try:
                            is_on = False
                            try:
                                is_on = t.is_selected()
                            except Exception:
                                pass
                            try:
                                aria = t.get_attribute("aria-checked")
                                if aria and aria.lower() == "true":
                                    is_on = True
                            except Exception:
                                pass
                            if is_on:
                                t.click()
                                steps += 1
                        except Exception:
                            continue
                    SAVE_XPATH = (
                        "//*[self::button or self::a or self::div or self::span]"
                        "[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'save')"
                        " or contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'confirm')"
                        " or contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'apply')]"
                    )
                    try:
                        savebtn = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, SAVE_XPATH))
                        )
                        savebtn.click()
                        steps += 1
                    except Exception:
                        continue
                return steps
            except Exception:
                continue
        return 0

    ############################## Added this ############################################

    def check_cookies(self, collection_type):
        website_domain = self.domain
        conn = sqlite3.connect(self.resultsDB.file_name)
        c = conn.cursor()
        c.execute("SELECT c.domain FROM cookies c JOIN cookie_collections cc ON cc.collection_num = c.collection_num WHERE cc.domain = :domain AND cc.type = :collection_type",{"domain":website_domain,"collection_type":collection_type})
        cookie_domains = c.fetchall()
        if cookie_domains:
            cookie_domains = cookie_domains
        else:
            cookie_domains = []
            
        domains = []
        first_party_cookies = 0
        third_party_cookies = 0
        for (cookie_domain,) in cookie_domains:
            #print(cookie_domain)
            cookie_domain = self.parse_domains(cookie_domain)
            if cookie_domain == website_domain:
                first_party_cookies += 1
            else:
                third_party_cookies += 1
            domains.append(cookie_domain)
        logging.debug("domains: "+str(domains))
        logging.debug("num domains: "+str(len(domains)))
        logging.debug("first_party_cookies: "+str(first_party_cookies))
        logging.debug("third_party_cookies: "+str(third_party_cookies))
        
        
        c.execute("SELECT cc.timestamp FROM cookie_collections cc WHERE cc.domain = :domain AND cc.type = :collection_type",{"domain":website_domain,"collection_type":collection_type})
        collection_timestamp = c.fetchone()
        if collection_timestamp:
            collection_timestamp = collection_timestamp[0]
        else:
            collection_timestamp = ""
        id_like_cookies = 0
        c.execute("SELECT value, expires FROM cookies c JOIN cookie_collections cc ON cc.collection_num = c.collection_num WHERE cc.domain = :domain AND cc.type = :collection_type",{"domain":website_domain,"collection_type":collection_type})
        cookie_value_expiry_pairs = c.fetchall()
        if cookie_value_expiry_pairs:
            cookie_value_expiry_pairs = cookie_value_expiry_pairs
        else:
            cookie_value_expiry_pairs = []
        
        for (value,expiry) in cookie_value_expiry_pairs:
            if is_id_cookie(collection_timestamp, value, expiry):
                id_like_cookies += 1
        c.execute("UPDATE cookie_collections SET num_first_party = :num_first_party, num_third_party = :num_third_party, num_id_like = :num_id_like WHERE domain = :domain AND type = :collection_type", {"num_first_party":first_party_cookies,"num_third_party":third_party_cookies, "num_id_like":id_like_cookies, "domain":self.domain, "collection_type":collection_type})
        conn.commit()
        conn.close() 
        return domains, first_party_cookies, third_party_cookies, id_like_cookies


    def parse_domains(self, raw_domain_value):
        result = tldextract.extract(raw_domain_value)
        return result.domain + "." + result.suffix

                
    def manual_validation(self, input_values, dark_patterns_desc):
        """ Function to prompt the user to manually validate the detected Dark Patterns.

        Args:
            input_values (dict[String->Boolean]): [description]
        """
        # Prompt the user to validate the auto DPs
        app = Checkbox_Input(input_values=input_values, input_descriptions=dark_patterns_desc, description="Check all the Auto Dark Patterns and then click confirm.", window_name="ADP")
        app.mainloop()
        # Update the value of each dark pattern to be the manually inputted value
        for dp in app.result:
            self.resultsDB.dark_patterns.update_value(self.domain, dp, str(app.result[dp].get()))
        
    
    def check_image(self, file_name):
        """ Function to determine wether an image is light or dark based on the average color of the image.

        Args:
            file_name (String): the file location of the image.

        Returns:
            String: 'light' or 'dark' specifiying the if the image is light or dark.
        """
        image = cv2.imread(file_name)
        blur = cv2.blur(image, (30, 30))  # With kernel size depending upon image size
        #cv2.imshow("yeet", blur) 
        #time.sleep(2)
        # Calculate average RGB values over all pixels
        mean = cv2.mean(blur)
        # Calculate average values of average RGB
        average = (mean[0] + mean[1] + mean[2])/3
        if average > 170:  # The range for a pixel's value in grayscale is (0-255), 127 lies midway
            return 'light' # (127 - 255) denotes light image
        else:
            return 'dark' # (0 - 127) denotes dark image        
        
        
    def check_image_greyscale(self, file_name):
        """ Function to determine wether an image is light or dark based on the average color of the greyscale image.

        Args:
            file_name (String): the file location of the image.

        Returns:
            String: 'light' or 'dark' specifiying the if the image is light or dark.
        """
        image = cv2.imread(file_name)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur = cv2.blur(image, (30, 30))  # With kernel size depending upon image size
        # Calculate average RGB values over all pixels
        mean = cv2.mean(blur)
        if mean[0] > 170:
            return 'light' # (170 - 255) denotes light image
        else:
            return 'dark' # (0 - 127) denotes dark image
        
        
    def find_distict(self, dictionary):
        """ Function to determine to return only distinct values in a dictionary, that is values which are not the same or a substring of any other value in the dictionary. 
        Empty string or None values are not returned.

        Args:
            dictionary (dict[int -> String]): the input dictionary mapping a key to a value.

        Returns:
            dict[int -> String]: a dictionary with only the distinct values kept.
        """
        # Remove any entries with an empty string or None value.
        dictionary = {i:dictionary[i] for i in dictionary if dictionary[i] != None and dictionary[i].strip() != ""}
        # Determine the set values
        array = set(dictionary.values())
        # Create a temp dict to store the results
        final_array = {a:dictionary[a] for a in dictionary}
        # For each item in the dicionary
        for item in dictionary:
            # Get the value of item in the dict
            value = dictionary[item]
            # Get all the values that are not the item
            not_item = array.difference({value})
            # For each item that is not the value
            for n in not_item:
                # If the item is contained within (substring of) another item then
                if value in n:
                    # Remove the item fron the results
                    if item in final_array:
                        final_array.pop(item)
        # Remove duplicates
        temp = {val : key for key, val in final_array.items()}
        res = {val : key for key, val in temp.items()}
        return res
  
# Helper function for fuzzy matching two strings
    @staticmethod
    def is_similar(a, b, threshold=0.8):
        """
        Check if two strings are similar based on a threshold similarity score.
        :param a: First string to compare.
        :param b: Second string to compare.
        :param threshold: Similarity threshold (default is 0.8).
        :return: True if similarity is greater than the threshold, False otherwise.
        """
        # Handle edge cases like empty strings or None values
        if not a or not b:
            return False
        return SequenceMatcher(None, a, b).ratio() > threshold

    @staticmethod
    def match_keywords(dialog_text, key_terms):
        """
        Check if any combination of key terms is present in the dialog text using fuzzy matching.
        :param dialog_text: The text from the cookie consent dialog.
        :param key_terms: List of tuples where each tuple contains terms to be matched with the dialog text.
        :return: True if any combination of key terms is present, False otherwise.
        """
        # Check if dialog_text is valid
        if not dialog_text:
            return False
        
        try:
            # Iterate over key term pairs and perform fuzzy matching
            return any(
                all(Automatic_Dark_Patterns.is_similar(term, dialog_text) or term in dialog_text for term in pair) for pair in key_terms
            )
        except Exception as e:
            # Log or print the exception to help with debugging
            print(f"Error in fuzzy matching: {e}")
            return False
        #################################### Storing  and getting the cookie  data for DP16 and DP18 #########################
    def get_cookie_details(self, collection_type):
        """
        Fetch cookie details including name, domain, path, expiry, httpOnly, sameSite, secure, and value for a given collection type.
        """
        cookies_details = []
        
        # Assuming cookies are fetched via self.resultsDB (adjust according to your DB schema)
        conn = sqlite3.connect(self.resultsDB.file_name)  # You can keep this unchanged
        c = conn.cursor()
        c.execute("""
            SELECT cookies.value, cookies.domain, cookies.path, cookies.expires, 
           cookies.httpOnly, cookies.sameSite, cookies.secure, cookies.name
            FROM cookies
            JOIN cookie_collections ON cookie_collections.collection_num = cookies.collection_num
            WHERE cookie_collections.domain = :domain 
            AND cookie_collections.type = :collection_type
            """, {"domain": self.domain, "collection_type": collection_type})
        
        cookies = c.fetchall()
        
        for cookie in cookies:
            cookie_info = {
                "name": cookie[7],  # Cookie name
                "domain": cookie[1],
                "path": cookie[2],
                "expiry": cookie[3],
                "httpOnly": cookie[4],  # Cookie is HTTP-only
                "sameSite": cookie[5],  # SameSite attribute
                "secure": cookie[6],    # Secure flag
                "value": cookie[0]      # Cookie value
            }
            cookies_details.append(cookie_info)
        
        conn.close()
        return cookies_details

    def save_cookie_details(self, cookies, filename):
        """ 
        Save the cookies to a JSON file in the 'Cookie_json' folder.
        """
    # Define the directory path for the Cookie_json folder
        folder_path = os.path.join(self.data_folder_name, 'Cookie_json')
    
    # Create the directory if it doesn't exist
        os.makedirs(folder_path, exist_ok=True)

    # Construct the full path to the JSON file
        file_path = os.path.join(folder_path, filename)
    
    # Write the cookies to the file
        with open(file_path, 'w') as json_file:
            json.dump(cookies, json_file, indent=4)
        
        logging.info(f"Cookies saved to {file_path}")

    def save_results_to_json(self, results, filename):
        """ Save the results to a JSON file. """
        file_path = os.path.join(self.data_folder_name, filename)
    
    # Create directory if it doesn't exist
        os.makedirs(self.data_folder_name, exist_ok=True)

    # Write the results to the file
        with open(file_path, 'w') as json_file:
            json.dump(results, json_file, indent=4)
    
        logging.info(f"Results saved to {file_path}")


        ############################### Storing data ends here ########################
