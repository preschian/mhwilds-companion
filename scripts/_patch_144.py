from pathlib import Path
p = Path(r"D:\Workspace\mhwilds-companion\mods\fieldguide-sos\fieldguide_sos.lua")
text = p.read_text(encoding="utf-8")
start = text.find('if phase == "post_search" then')
# include leading whitespace on that line
line_start = text.rfind("\n", 0, start) + 1
end = text.find('if phase == "wait_order" then', start)
end_line = text.rfind("\n", 0, end) + 1
print("start", line_start, "end", end_line)
print("HEAD", repr(text[line_start:line_start+60]))
print("TAIL", repr(text[end_line:end_line+40]))
new_block = '''  if phase == "post_search" then
    if not action_ready() then return end
    local cat = current_category()
    note("post_search cat=" .. tostring(cat))
    if cat == CAT_SEARCH_RESCUE then
      state.cat_fixed = true
      set_phase("wait_list", "cat=12 ok — wait hasSR")
      return
    end
    -- NEVER setQuestListInCategory after SearchRescure — crashes (log 13:56:21)
    local ok, detail = soft_rescue_category()
    arm_gap()
    state.cat_fixed = true
    set_phase("wait_list", tostring(detail) .. " — wait hasSR")
    return
  end

  if phase == "wait_list" then
    local view, _, detail = pick_rescue_view()
    if view then
      if not action_ready() then
        state.msg = string.format("hasSR — jeda %.1fs cat=%s", math.max(0, state.next_action_at - now), tostring(current_category()))
        return
      end
      set_phase("detail", tostring(detail) .. " cat=" .. tostring(current_category()))
      return
    end
    state.msg = "wait hasSR cat=" .. tostring(current_category()) .. " " .. tostring(detail)
    if now > state.deadline then
      state.deadline = now + cfg.retry_search_s
      set_phase("prep_cat", "retry from cat")
    end
    return
  end

  if phase == "detail" then
    if not action_ready() then return end
    local ok, detail = do_detail()
    arm_gap()
    if not ok then
      state.msg = tostring(detail)
      if now > state.deadline then
        set_phase("prep_cat", "detail fail: " .. tostring(detail))
      end
      return
    end
    set_phase("decide", detail .. " — jeda 3s")
    return
  end

  if phase == "decide" then
    if not action_ready() then return end
    local ok, detail = do_decide()
    arm_gap()
    if not ok then
      state.msg = tostring(detail)
      if now > state.deadline then
        set_phase("prep_cat", "decide fail: " .. tostring(detail))
      end
      return
    end
    state.deadline = now + cfg.wait_join_s
    state.ordered = false
    set_phase("wait_order", detail .. " — wait 162+169+170, jeda 3s, order")
    return
  end

'''
text2 = text[:line_start] + new_block + text[end_line:]
p.write_text(text2, encoding="utf-8")
print("ok", "force after search", "force_rescue_category()" in text2[text2.find("post_search"):text2.find("wait_order")])
