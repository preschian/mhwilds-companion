-- Skip startup logos/warnings (app.GUI010001).
local t = sdk.find_type_definition("app.GUI010001")
if not t then
  log.error("skip_intro: app.GUI010001 missing")
  return
end

local on_open = t:get_method("onOpen()")
local vis = t:get_method("guiVisibleUpdate()")
if not on_open or not vis then
  log.error("skip_intro: method missing")
  return
end

sdk.hook(on_open, function(args)
  local obj = sdk.to_managed_object(args[2])
  local storage = thread.get_hook_storage()
  storage["this"] = obj
  log.info("skip_intro: GUI Flow was " .. tostring(obj and obj._Flow))
end, function(retval)
  local obj = thread.get_hook_storage()["this"]
  if obj then
    obj._Flow = 5
    obj:toClose()
  end
  return retval
end)

sdk.hook(vis, function(args)
  local obj = sdk.to_managed_object(args[2])
  if not obj then return end
  obj._Skip = true
  obj._EnableSkip = true
end)
