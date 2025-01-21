from module.automation import auto


class EventHandling:

    @staticmethod
    def decision_event_handling():
        if best_option := auto.find_element("event/very_high.png"):
            auto.mouse_action_with_pos(best_option)
        elif best_option := auto.find_element("event/high.png"):
            auto.mouse_action_with_pos(best_option)
        elif best_option := auto.find_element("event/normal.png"):
            auto.mouse_action_with_pos(best_option)
        elif best_option := auto.find_element("event/low.png"):
            auto.mouse_action_with_pos(best_option)
        elif best_option := auto.find_element("event/very_low.png"):
            auto.mouse_action_with_pos(best_option)
