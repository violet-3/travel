"""Offline regression coverage for LangChain structured Agent outputs."""

import os
import unittest

# Agent module imports config at import time. Force inert test-only settings before
# importing it so a developer's .env cannot leak a key or influence this suite.
os.environ["AMAP_WEATHER_KEY"] = ""
os.environ["AMAP_JS_API_KEY"] = ""
os.environ["AMAP_SECRET"] = ""
os.environ["TRAVEL_LLM_URL"] = "http://127.0.0.1:9/v1"
os.environ["TRAVEL_LLM_KEY"] = "offline-test-key"
os.environ["TRAVEL_LLM_MODEL"] = "offline-test-model"

from agents.attraction_culture import (  # noqa: E402
    AgentOutputError,
    AttractionRecommenderAgent,
    CultureEngineAgent,
    CultureList,
    SpotList,
)
from models.schemas import CultureData, Spot  # noqa: E402


class AgentOutputParserTests(unittest.TestCase):
    def setUp(self):
        # Parsing does not call the model; a non-null stub avoids constructing the
        # process-wide default client.
        self.spot_agent = AttractionRecommenderAgent(llm=object())
        self.culture_agent = CultureEngineAgent(llm=object())

    def test_spot_output_shapes_preserve_content(self):
        spot = Spot(name="殷墟", city="安阳", tips="殷商都城遗址")
        spot_dict = {"name": "殷墟", "city": "安阳", "tips": "殷商都城遗址"}
        variants = [
            SpotList(items=[spot]),
            {"items": [spot_dict]},
            {"items": [spot]},
            [spot_dict],
            [spot],
            spot_dict,
            '{"items":[{"name":"殷墟","city":"安阳","tips":"殷商都城遗址"}]}',
            '[{"name":"殷墟","city":"安阳","tips":"殷商都城遗址"}]',
            '```json\n{"items":[{"name":"殷墟","city":"安阳","tips":"殷商都城遗址"}]}\n```',
        ]
        for value in variants:
            with self.subTest(value_type=type(value).__name__, value=value):
                parsed = self.spot_agent.parse_output(value)
                self.assertEqual(len(parsed), 1)
                self.assertEqual(parsed[0].name, "殷墟")
                self.assertEqual(parsed[0].tips, "殷商都城遗址")

    def test_culture_output_shapes_preserve_content(self):
        culture = CultureData(city="安阳", cuisine={"must_eat": [{"name": "扁粉菜"}]})
        culture_dict = {"city": "安阳", "cuisine": {"must_eat": [{"name": "扁粉菜"}]}}
        variants = [
            CultureList(items=[culture]),
            {"items": [culture_dict]},
            {"items": [culture]},
            [culture_dict],
            [culture],
            culture_dict,
            '{"items":[{"city":"安阳","cuisine":{"must_eat":[{"name":"扁粉菜"}]}}]}',
            '[{"city":"安阳","cuisine":{"must_eat":[{"name":"扁粉菜"}]}}]',
        ]
        for value in variants:
            with self.subTest(value_type=type(value).__name__, value=value):
                parsed = self.culture_agent.parse_output(value)
                self.assertEqual(len(parsed), 1)
                self.assertEqual(parsed[0].city, "安阳")
                self.assertEqual(parsed[0].cuisine["must_eat"][0]["name"], "扁粉菜")

    def test_empty_invalid_and_truncated_outputs_raise_clear_errors(self):
        bad_spots = [
            None,
            "",
            "   ",
            [],
            {"items": []},
            {"items": "not a list"},
            {"items": [{}]},
            [Spot()],
            [Spot(name="", city="安阳")],
            {"items": [{"name": "", "city": "安阳"}]},
            '{"items":[{"name":"殷墟"}',
        ]
        for value in bad_spots:
            with self.subTest(agent="spots", value=value):
                with self.assertRaises(AgentOutputError):
                    self.spot_agent.parse_output(value)

        bad_cultures = [
            None,
            "",
            [],
            {"items": []},
            {"items": [{}]},
            [CultureData()],
            '{"items":[{"city":"安阳"}',
        ]
        for value in bad_cultures:
            with self.subTest(agent="culture", value=value):
                with self.assertRaises(AgentOutputError):
                    self.culture_agent.parse_output(value)


if __name__ == "__main__":
    unittest.main()
