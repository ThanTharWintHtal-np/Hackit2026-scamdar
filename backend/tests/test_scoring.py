import unittest

from app.scoring import analyze_text, similarity


class ScoringTests(unittest.TestCase):
    def test_exact_demo_message_is_high_and_explainable(self):
        result = analyze_text("Your SingPost parcel has been detained. Pay $2.03 today to arrange delivery at http://example-suspicious-link.test", community_matches=8)
        self.assertEqual(result["level"], "High")
        self.assertEqual(result["score"], 92)
        codes = {item["code"] for item in result["signals"]}
        self.assertTrue({"urgency", "payment", "delivery_impersonation", "brand_impersonation", "suspicious_domain", "campaign_activity"}.issubset(codes))

    def test_score_stays_capped(self):
        result = analyze_text("SingPost parcel detained today. Pay now, enter password, OTP, PIN, Singpass and credit card at http://bad.zip", community_matches=30)
        self.assertLessEqual(result["score"], 100)
        self.assertEqual(result["level"], "Critical")

    def test_ordinary_text_is_not_automatically_scam(self):
        result = analyze_text("The community meeting is at the library on Saturday.")
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["level"], "Low")

    def test_similarity_matches_campaign_wording(self):
        score = similarity("SingPost parcel detained pay delivery fee today", "Your SingPost parcel has been detained. Pay delivery fee today")
        self.assertGreater(score, 0.55)

    def test_unrelated_messages_have_lower_similarity(self):
        score = similarity("SingPost parcel detained pay delivery today", "A recruiter asks for bank login and OTP to release salary")
        self.assertLess(score, 0.2)

    def test_known_official_domain_is_not_flagged_as_a_lookalike(self):
        result = analyze_text("Check your DBS account at https://www.dbs.com.sg/secure")
        self.assertNotIn("brand_like_domain", {item["code"] for item in result["signals"]})


if __name__ == "__main__": unittest.main()
