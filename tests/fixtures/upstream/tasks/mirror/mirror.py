# Static method references from official e1d1749; not imported.
class Mirror:

    def _log_floor_time(self, end_time, floor):
        """输出当前楼层的耗时"""
        if self.current_floor_start_time is None:
            return
        msg = f'第{floor}层' if floor > 0 else '楼层未知'
        if not self.current_floor_time_complete:
            msg += '，计时不完整'
        to_log_with_time(msg, end_time - self.current_floor_start_time)

    @begin_and_finish_time_log(task_name='镜牢寻路')
    def search_road(self):
        if cfg.mirror_keyboard_simple_pathfinding:
            if search_road_simple_keyboard():
                return True
            log.debug('简单键盘寻路失败，回退到常规寻路')
        try:
            if (next_node := self.mirror_map.get_next_step()):
                if next_node is True:
                    return True
                if self.mirror_map.enter_next_node(next_node):
                    return True
            log.debug('未能构建路线图，尝试使用最近节点法重新寻路')
        except Exception as e:
            log.debug(f'使用onnx模型寻路出错:{e}')
        finally:
            auto.mouse_to_blank()
        try:
            for _ in range(3):
                while auto.take_screenshot() is None:
                    continue
                if search_road_default_distance():
                    sleep(1)
                    return True
                if auto.click_element('mirror/road_in_mir/enter_assets.png'):
                    return True
                if retry() is False:
                    return False
            for _ in range(3):
                if cfg.background_click:
                    continue
                while auto.take_screenshot() is None:
                    continue
                if search_road_farthest_distance():
                    sleep(1)
                    return True
                if retry() is False:
                    return False
        except InputAttributeError as e:
            log.error(f'寻路出错:{e}, 尝试重进镜牢')
            pass
        except Exception as e:
            log.error(f'寻路出错:{e}')
            return False
        if auto.click_element('mirror/road_in_mir/enter_assets.png', take_screenshot=True):
            return True
        start_time = time.time()
        log.info('寻路出错, 尝试重进镜牢')
        while True:
            from tasks.base.retry import check_times
            if auto.take_screenshot() is None:
                continue
            if auto.get_restore_time() is not None:
                start_time = max(start_time, auto.get_restore_time())
            if check_times(start_time):
                back_init_menu()
                return False
            auto.mouse_to_blank()
            if auto.click_element('mirror/road_in_mir/enter_assets.png'):
                return True
            if auto.click_element('home/drive_assets.png') or auto.find_element('home/window_assets.png'):
                sleep(0.5)
                break
            if auto.click_element('mirror/road_in_mir/towindow&forfeit_confirm_assets.png'):
                break
            if auto.click_element('mirror/road_in_mir/to_window_assets.png', threshold=0.75):
                continue
            if auto.click_element('mirror/road_in_mir/setting_assets.png'):
                sleep(1)
                continue
            if retry() is False:
                return False
