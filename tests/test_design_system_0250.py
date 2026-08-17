from __future__ import annotations

import unittest

from carendmr.ui.design_system import (
    FOCUS_THICKNESS,
    PALETTE,
    action_options,
    focus_options,
    input_options,
    information_options,
    selection_options,
)


class DesignSystem0250Tests(unittest.TestCase):
    def test_focus_is_visibly_stronger_than_resting_border(self) -> None:
        self.assertEqual(focus_options(True)["highlightthickness"], FOCUS_THICKNESS)
        self.assertGreater(
            int(focus_options(True)["highlightthickness"]),
            int(focus_options(False)["highlightthickness"]),
        )
        self.assertEqual(focus_options(True)["highlightbackground"], PALETTE.focus)

    def test_element_classes_have_distinct_visual_semantics(self) -> None:
        information = information_options()
        editable_input = input_options(enabled=True)
        active_selection = selection_options(active=True, enabled=True)
        action = action_options(enabled=True)

        self.assertNotEqual(information["bg"], editable_input["bg"])
        self.assertNotEqual(editable_input["bg"], active_selection["bg"])
        self.assertNotEqual(active_selection["bg"], action["bg"])
        self.assertEqual(information["cursor"], "arrow")
        self.assertEqual(active_selection["cursor"], "hand2")
        self.assertEqual(action["cursor"], "hand2")

    def test_disabled_controls_look_and_behave_disabled(self) -> None:
        self.assertEqual(selection_options(active=True, enabled=False)["cursor"], "arrow")
        self.assertEqual(action_options(enabled=False)["cursor"], "arrow")
        self.assertEqual(input_options(enabled=False)["bg"], PALETTE.input_disabled_bg)

    def test_critical_action_is_visually_distinct(self) -> None:
        self.assertEqual(action_options(critical=True, enabled=True)["bg"], PALETTE.critical)
        self.assertNotEqual(
            action_options(critical=True, enabled=True)["bg"],
            action_options(critical=False, enabled=True)["bg"],
        )


if __name__ == "__main__":
    unittest.main()
