extends Node2D
## Quackers — Godot edition. No AI, ALL juice.
##
## The duck lives in a small transparent always-on-top window and walks
## around the desktop by moving that window. Every movement is animated
## with squash & stretch, waddle rotation, hops, backflips and real
## throw-physics with bouncing.

enum State { IDLE, WALK, SLEEP, DRAG, FALL, JUICE }

const DUCK_H := 120.0            # sprite height at scale 1
const FEET_Y := 344.0            # duck feet baseline inside the window
const CENTER_X := 160.0
const GRAVITY := 2600.0
const BOUNCE_DAMP := 0.42
const THROW_MAX := 2600.0

const QUACK_LINES: Array[String] = [
	"QUACK!",
	"Your desktop is my pond now.",
	"I could carry you over a small gap. A disproportionately small one.",
	"*happy waddle noises*",
	"Bread would be great right about now.",
	"I know 37 kinds of quack. This is one of them: QUACK.",
	"Working hard? I'm hardly waddling.",
	"Did you know I can do a backflip? Watch me sometime.",
	"The early duck gets the crumb.",
	"Throw me. I dare you. I have PHYSICS.",
	"*inspects your taskbar* ...acceptable.",
	"Quack quack quack. That was a haiku.",
	"I'm not procrastinating, I'm PROFESSIONALLY idling.",
	"One day I will fly. Today I waddle.",
	"You've been petted by... wait, that's my line backwards.",
]

const PET_LINES: Array[String] = [
	"<3 QUACK! That's the spot!",
	"*happy tail wiggle* More pets!",
	"Best. Human. Ever. <3",
	"I am now legally your best friend. No take-backs.",
	"*purrs* ...wait, ducks don't purr. *quacks affectionately*",
]

# ── Nodes ────────────────────────────────────────────────────────────────────
var pivot: Node2D
var sprite: AnimatedSprite2D
var fx: Node2D
var bubble: PanelContainer
var bubble_label: Label
var menu: PopupMenu
var settings_menu: PopupMenu

# ── State ────────────────────────────────────────────────────────────────────
var state: int = State.IDLE
var fpos := Vector2.ZERO          # float window position (authoritative)
var vel := Vector2.ZERO           # px/s while falling
var ang_vel := 0.0
var walk_dir := 1                 # -1 left, +1 right (sprites face LEFT)
var walk_time_left := 0.0
var t := 0.0                      # global clock
var idle_for := 0.0
var behavior_cd := 3.0
var quack_cd := 20.0
var z_cd := 0.0
var usable := Rect2i(0, 0, 1920, 1080)
var screen_refresh_cd := 0.0
var juice_busy := false           # a hop/flip/pet tween owns the transform
var air_tween: Tween
var bubble_tween: Tween
var bubble_visible := false

# drag / throw
var pressing := false
var dragging := false
var press_pos := Vector2.ZERO
var grab_offset := Vector2i.ZERO
var drag_samples: Array = []      # [msec, Vector2 screen pos]
var suppress_click := false

# settings
var cfg_size := 1                 # 0 small 1 medium 2 large
var cfg_speed := 1                # 0 chill 1 normal 2 zoomies
var cfg_gravity := true
var cfg_chatty := true

var heart_tex: ImageTexture
var dust_tex: ImageTexture

# ─────────────────────────────────────────────────────────────────────────────

func _ready() -> void:
	Engine.max_fps = 60
	_build_textures()
	_build_scene()
	_load_settings()
	_apply_size()

	var w := get_window()
	w.transparent = true
	w.borderless = true
	w.always_on_top = true

	_refresh_screen_rect()
	var win_w := w.size.x
	fpos = Vector2(
		usable.position.x + usable.size.x * randf_range(0.3, 0.7) - win_w * 0.5,
		_ground_y()
	)
	_apply_window_pos()

	sprite.play("idle")
	_say(QUACK_LINES[randi() % QUACK_LINES.size()])

func _build_scene() -> void:
	pivot = Node2D.new()
	pivot.position = Vector2(CENTER_X, FEET_Y)
	add_child(pivot)

	sprite = AnimatedSprite2D.new()
	sprite.position = Vector2(0, -DUCK_H * 0.5)
	sprite.sprite_frames = _build_frames()
	sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	pivot.add_child(sprite)

	fx = Node2D.new()
	add_child(fx)

	_build_bubble()
	_build_menu()

func _build_frames() -> SpriteFrames:
	var frames := SpriteFrames.new()
	frames.remove_animation("default")

	frames.add_animation("idle")
	frames.add_frame("idle", load("res://sprites/idle.png"))
	frames.set_animation_speed("idle", 1)

	frames.add_animation("wave")
	frames.add_frame("wave", load("res://sprites/wave.png"))
	frames.set_animation_speed("wave", 1)

	frames.add_animation("walk")
	for i in range(4):
		frames.add_frame("walk", load("res://sprites/walk_%d.png" % i))
	frames.set_animation_speed("walk", 9)
	frames.set_animation_loop("walk", true)

	return frames

func _build_bubble() -> void:
	bubble = PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(1.0, 0.98, 0.88, 0.96)
	sb.border_color = Color(0.91, 0.70, 0.23)
	sb.set_border_width_all(2)
	sb.set_corner_radius_all(12)
	sb.content_margin_left = 12.0
	sb.content_margin_right = 12.0
	sb.content_margin_top = 8.0
	sb.content_margin_bottom = 8.0
	bubble.add_theme_stylebox_override("panel", sb)

	bubble_label = Label.new()
	bubble_label.add_theme_color_override("font_color", Color(0.24, 0.18, 0.06))
	bubble_label.add_theme_font_size_override("font_size", 13)
	bubble_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	bubble_label.custom_minimum_size = Vector2(0, 0)
	bubble.add_child(bubble_label)

	bubble.hide()
	add_child(bubble)

func _build_menu() -> void:
	menu = PopupMenu.new()
	menu.add_item("Pet me  <3", 1)
	menu.add_item("Do a trick!", 2)
	menu.add_item("Say something", 3)
	menu.add_item("Nap time (toggle)", 4)
	menu.add_separator()

	settings_menu = PopupMenu.new()
	settings_menu.name = "SettingsSub"
	settings_menu.add_radio_check_item("Small duck", 10)
	settings_menu.add_radio_check_item("Medium duck", 11)
	settings_menu.add_radio_check_item("LARGE duck", 12)
	settings_menu.add_separator()
	settings_menu.add_radio_check_item("Chill pace", 20)
	settings_menu.add_radio_check_item("Normal pace", 21)
	settings_menu.add_radio_check_item("ZOOMIES", 22)
	settings_menu.add_separator()
	settings_menu.add_check_item("Throw physics", 30)
	settings_menu.add_check_item("Chatty duck", 31)
	settings_menu.id_pressed.connect(_on_settings_id)
	menu.add_child(settings_menu)
	menu.add_submenu_item("Settings", "SettingsSub")

	menu.add_separator()
	menu.add_item("Quit", 99)
	menu.id_pressed.connect(_on_menu_id)
	add_child(menu)
	_sync_menu_checks()

func _build_textures() -> void:
	heart_tex = _pixel_tex([
		" XX XX ",
		"XXXXXXX",
		"XXXXXXX",
		" XXXXX ",
		"  XXX  ",
		"   X   ",
	], Color(1.0, 0.42, 0.55))
	dust_tex = _pixel_tex([
		" XX ",
		"XXXX",
		"XXXX",
		" XX ",
	], Color(0.82, 0.78, 0.70))

func _pixel_tex(rows: Array, col: Color) -> ImageTexture:
	var h := rows.size()
	var w: int = rows[0].length()
	var img := Image.create(w, h, false, Image.FORMAT_RGBA8)
	for y in range(h):
		var row: String = rows[y]
		for x in range(w):
			if row[x] == "X":
				img.set_pixel(x, y, col)
	return ImageTexture.create_from_image(img)

# ── Settings ─────────────────────────────────────────────────────────────────

func _load_settings() -> void:
	var cf := ConfigFile.new()
	if cf.load("user://duck.cfg") == OK:
		cfg_size = cf.get_value("duck", "size", 1)
		cfg_speed = cf.get_value("duck", "speed", 1)
		cfg_gravity = cf.get_value("duck", "gravity", true)
		cfg_chatty = cf.get_value("duck", "chatty", true)

func _save_settings() -> void:
	var cf := ConfigFile.new()
	cf.set_value("duck", "size", cfg_size)
	cf.set_value("duck", "speed", cfg_speed)
	cf.set_value("duck", "gravity", cfg_gravity)
	cf.set_value("duck", "chatty", cfg_chatty)
	cf.save("user://duck.cfg")

func _base_scale() -> float:
	var sizes: Array[float] = [0.78, 1.0, 1.3]
	return sizes[clampi(cfg_size, 0, 2)]

func _walk_speed() -> float:
	var speeds: Array[float] = [42.0, 75.0, 135.0]
	return speeds[clampi(cfg_speed, 0, 2)]

func _apply_size() -> void:
	var b := _base_scale()
	pivot.scale = Vector2(b, b)
	_update_passthrough()

func _update_passthrough() -> void:
	var b := _base_scale()
	var w2 := 80.0 * b
	var top := FEET_Y - 138.0 * b
	get_window().mouse_passthrough_polygon = PackedVector2Array([
		Vector2(CENTER_X - w2, top),
		Vector2(CENTER_X + w2, top),
		Vector2(CENTER_X + w2, FEET_Y + 16.0),
		Vector2(CENTER_X - w2, FEET_Y + 16.0),
	])

func _sync_menu_checks() -> void:
	for id in [10, 11, 12]:
		settings_menu.set_item_checked(settings_menu.get_item_index(id), id - 10 == cfg_size)
	for id in [20, 21, 22]:
		settings_menu.set_item_checked(settings_menu.get_item_index(id), id - 20 == cfg_speed)
	settings_menu.set_item_checked(settings_menu.get_item_index(30), cfg_gravity)
	settings_menu.set_item_checked(settings_menu.get_item_index(31), cfg_chatty)

func _on_settings_id(id: int) -> void:
	match id:
		10, 11, 12: cfg_size = id - 10; _apply_size(); do_hop()
		20, 21, 22: cfg_speed = id - 20
		30: cfg_gravity = not cfg_gravity
		31: cfg_chatty = not cfg_chatty
	_sync_menu_checks()
	_save_settings()

func _on_menu_id(id: int) -> void:
	match id:
		1: pet()
		2: do_flip()
		3: _say(QUACK_LINES[randi() % QUACK_LINES.size()])
		4:
			if state == State.SLEEP: wake()
			else: go_sleep()
		99: get_tree().quit()

# ── Screen / window helpers ──────────────────────────────────────────────────

func _refresh_screen_rect() -> void:
	var r := DisplayServer.screen_get_usable_rect(get_window().current_screen)
	if r.size.x > 100 and r.size.y > 100:
		usable = r

func _ground_y() -> float:
	return float(usable.position.y + usable.size.y - get_window().size.y)

func _apply_window_pos() -> void:
	var w := get_window()
	var min_x := float(usable.position.x)
	var max_x := float(usable.position.x + usable.size.x - w.size.x)
	var min_y := float(usable.position.y)
	fpos.x = clampf(fpos.x, min_x, max_x)
	fpos.y = clampf(fpos.y, min_y, _ground_y())
	w.position = Vector2i(fpos)

# ── Main loop ────────────────────────────────────────────────────────────────

func _process(delta: float) -> void:
	t += delta
	screen_refresh_cd -= delta
	if screen_refresh_cd <= 0.0:
		screen_refresh_cd = 2.0
		_refresh_screen_rect()

	match state:
		State.IDLE: _tick_idle(delta)
		State.WALK: _tick_walk(delta)
		State.SLEEP: _tick_sleep(delta)
		State.DRAG: _tick_drag(delta)
		State.FALL: _tick_fall(delta)
		State.JUICE: pass   # a tween owns the duck right now

	if bubble_visible:
		_layout_bubble()
	queue_redraw()

func _tick_idle(delta: float) -> void:
	idle_for += delta
	behavior_cd -= delta
	quack_cd -= delta

	if not juice_busy:
		# breathing
		var b := _base_scale()
		var s := 0.015 * sin(t * 2.2)
		pivot.scale = Vector2(b * (1.0 - s), b * (1.0 + s))
		pivot.rotation = 0.0

	if idle_for > 90.0:
		go_sleep()
		return

	if cfg_chatty and quack_cd <= 0.0:
		quack_cd = randf_range(25.0, 55.0)
		_say(QUACK_LINES[randi() % QUACK_LINES.size()])

	if behavior_cd <= 0.0:
		behavior_cd = randf_range(2.5, 6.0)
		var roll := randf()
		if roll < 0.38: _start_walk()
		elif roll < 0.52: do_hop()
		elif roll < 0.59: do_flip()
		elif roll < 0.76: _look_around()
		elif roll < 0.88: _preen()
		# else: just vibe

func _tick_walk(delta: float) -> void:
	walk_time_left -= delta
	var speed := _walk_speed()
	fpos.x += walk_dir * speed * delta

	var min_x := float(usable.position.x)
	var max_x := float(usable.position.x + usable.size.x - get_window().size.x)
	if fpos.x <= min_x or fpos.x >= max_x:
		walk_dir = -walk_dir
		sprite.flip_h = walk_dir > 0
	_apply_window_pos()

	if not juice_busy:
		# waddle: rock side to side + tiny bounce, synced to footsteps
		var b := _base_scale()
		var wt := t * (7.0 + speed * 0.05)
		pivot.rotation = sin(wt) * 0.085
		pivot.scale = Vector2(b, b * (1.0 + 0.02 * absf(sin(wt))))

	if walk_time_left <= 0.0:
		_stop_walk()

func _tick_sleep(delta: float) -> void:
	z_cd -= delta
	if not juice_busy:
		var b := _base_scale()
		var s := 0.02 * sin(t * 1.1)
		pivot.scale = Vector2(b * (1.0 - s), b * (1.0 + s))
	if z_cd <= 0.0:
		z_cd = 1.3
		_spawn_z()

func _tick_drag(delta: float) -> void:
	var mouse := DisplayServer.mouse_get_position()
	fpos = Vector2(mouse - grab_offset)
	_apply_window_pos()
	drag_samples.append([Time.get_ticks_msec(), Vector2(mouse)])
	while drag_samples.size() > 6:
		drag_samples.pop_front()

	# dangle: tilt against horizontal motion, stretch a little
	var vx := 0.0
	if drag_samples.size() >= 2:
		var a: Array = drag_samples[0]
		var c: Array = drag_samples[drag_samples.size() - 1]
		var dt_ms: float = maxf(1.0, float(c[0]) - float(a[0]))
		vx = (c[1].x - a[1].x) / dt_ms * 1000.0
	var b := _base_scale()
	sprite.rotation = lerpf(sprite.rotation, clampf(-vx * 0.0006, -0.4, 0.4), 10.0 * delta)
	pivot.scale = pivot.scale.lerp(Vector2(b * 0.93, b * 1.08), 10.0 * delta)

func _tick_fall(delta: float) -> void:
	vel.y += GRAVITY * delta
	fpos += vel * delta
	sprite.rotation += ang_vel * delta   # tumble around the body's center

	var w := get_window()
	var min_x := float(usable.position.x)
	var max_x := float(usable.position.x + usable.size.x - w.size.x)
	var min_y := float(usable.position.y)
	var ground := _ground_y()

	if fpos.x <= min_x or fpos.x >= max_x:
		fpos.x = clampf(fpos.x, min_x, max_x)
		vel.x = -vel.x * 0.6
		ang_vel = -ang_vel * 0.7
	if fpos.y <= min_y:
		fpos.y = min_y
		vel.y = absf(vel.y) * 0.5

	if fpos.y >= ground:
		fpos.y = ground
		var impact := absf(vel.y)
		if impact > 160.0:
			vel.y = -impact * BOUNCE_DAMP
			vel.x *= 0.72
			ang_vel *= 0.6
			_impact_squash(impact)
			_spawn_dust(6)
		else:
			_land_settle()
	_apply_window_pos()

func _land_settle() -> void:
	vel = Vector2.ZERO
	ang_vel = 0.0
	state = State.IDLE
	idle_for = 0.0
	_spawn_dust(4)
	sprite.rotation = wrapf(sprite.rotation, -PI, PI)
	var tw := create_tween()
	tw.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tw.tween_property(sprite, "rotation", 0.0, 0.35)
	var b := _base_scale()
	tw.parallel().tween_property(pivot, "scale", Vector2(b, b), 0.35)
	sprite.play("idle")
	if randf() < 0.5:
		_say(["Ouch. QUACK.", "I meant to do that.", "10/10 landing. The judges are ducks.",
			"WHEEE— I mean, how dare you."][randi() % 4])

func _impact_squash(impact: float) -> void:
	var b := _base_scale()
	var k := clampf(impact / 1800.0, 0.12, 0.4)
	var tw := create_tween()
	tw.tween_property(pivot, "scale", Vector2(b * (1.0 + k), b * (1.0 - k)), 0.06)
	tw.tween_property(pivot, "scale", Vector2(b, b), 0.18).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)

# ── Behaviors ────────────────────────────────────────────────────────────────

func _start_walk() -> void:
	state = State.WALK
	walk_dir = [-1, 1][randi() % 2]
	sprite.flip_h = walk_dir > 0
	walk_time_left = randf_range(2.0, 6.0)
	sprite.play("walk")

func _stop_walk() -> void:
	state = State.IDLE
	idle_for = 0.0
	sprite.play("idle")
	pivot.rotation = 0.0

func go_sleep() -> void:
	_kill_air()
	state = State.SLEEP
	sprite.play("idle")
	sprite.modulate = Color(0.75, 0.75, 0.85)
	z_cd = 0.4
	_say("zzz...")

func wake() -> void:
	if state != State.SLEEP:
		return
	state = State.IDLE
	idle_for = 0.0
	sprite.modulate = Color.WHITE
	do_hop(18.0)
	_say("*startled quack* I WAS AWAKE! Totally.")

func do_hop(height := 30.0) -> void:
	if juice_busy or state in [State.DRAG, State.FALL]:
		return
	juice_busy = true
	var prev_state := state
	state = State.JUICE
	var b := _base_scale()

	air_tween = create_tween()
	# anticipate: crouch
	air_tween.tween_property(pivot, "scale", Vector2(b * 1.12, b * 0.86), 0.09).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	# launch: stretch + up
	air_tween.tween_property(pivot, "scale", Vector2(b * 0.90, b * 1.14), 0.10)
	air_tween.parallel().tween_property(pivot, "position:y", FEET_Y - height, 0.20).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	# fall back down
	air_tween.tween_property(pivot, "position:y", FEET_Y, 0.17).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	# land squash
	air_tween.tween_property(pivot, "scale", Vector2(b * 1.2, b * 0.8), 0.07)
	air_tween.tween_callback(func(): _spawn_dust(3))
	# springy recover
	air_tween.tween_property(pivot, "scale", Vector2(b, b), 0.28).set_trans(Tween.TRANS_ELASTIC).set_ease(Tween.EASE_OUT)
	air_tween.tween_callback(func():
		juice_busy = false
		if state == State.JUICE:
			state = prev_state if prev_state != State.JUICE else State.IDLE
	)

func do_flip() -> void:
	if juice_busy or state in [State.DRAG, State.FALL]:
		return
	juice_busy = true
	var prev_state := state
	state = State.JUICE
	var b := _base_scale()
	var dir := -1.0 if sprite.flip_h else 1.0

	air_tween = create_tween()
	air_tween.tween_property(pivot, "scale", Vector2(b * 1.14, b * 0.84), 0.11)
	air_tween.tween_property(pivot, "scale", Vector2(b * 0.9, b * 1.12), 0.08)
	air_tween.parallel().tween_property(pivot, "position:y", FEET_Y - 56.0, 0.26).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	# Spin the SPRITE (centered) so the flip rotates around the duck's body,
	# not its feet — feet-pivot flips read as "tipping over", not acrobatics.
	air_tween.parallel().tween_property(sprite, "rotation", TAU * dir, 0.50)
	air_tween.tween_property(pivot, "position:y", FEET_Y, 0.22).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	air_tween.tween_callback(func():
		sprite.rotation = 0.0
		_spawn_dust(5)
	)
	air_tween.tween_property(pivot, "scale", Vector2(b * 1.24, b * 0.76), 0.07)
	air_tween.tween_property(pivot, "scale", Vector2(b, b), 0.3).set_trans(Tween.TRANS_ELASTIC).set_ease(Tween.EASE_OUT)
	air_tween.tween_callback(func():
		juice_busy = false
		if state == State.JUICE:
			state = prev_state if prev_state != State.JUICE else State.IDLE
		if randf() < 0.6:
			_say(["Nailed it.", "QUACK-robatics!", "Olympic committee, call me."][randi() % 3])
	)

func pet() -> void:
	wake()
	_spawn_hearts(6)
	_say(PET_LINES[randi() % PET_LINES.size()])
	if not juice_busy and not (state in [State.DRAG, State.FALL]):
		juice_busy = true
		var prev_state := state
		state = State.JUICE
		var tw := create_tween()
		for i in range(3):
			tw.tween_property(pivot, "rotation", 0.12, 0.07)
			tw.tween_property(pivot, "rotation", -0.12, 0.07)
		tw.tween_property(pivot, "rotation", 0.0, 0.08)
		tw.tween_callback(func():
			juice_busy = false
			if state == State.JUICE:
				state = prev_state if prev_state != State.JUICE else State.IDLE
		)

func _look_around() -> void:
	sprite.flip_h = not sprite.flip_h
	var tw := create_tween()
	tw.tween_interval(randf_range(0.6, 1.4))
	tw.tween_callback(func():
		if state == State.IDLE:
			sprite.flip_h = not sprite.flip_h
	)

func _preen() -> void:
	if juice_busy:
		return
	sprite.play("wave")
	var tw := create_tween()
	tw.tween_interval(0.9)
	tw.tween_callback(func():
		if state == State.IDLE:
			sprite.play("idle")
	)

func _kill_air() -> void:
	if air_tween and air_tween.is_valid():
		air_tween.kill()
	juice_busy = false
	pivot.position = Vector2(CENTER_X, FEET_Y)
	pivot.rotation = 0.0
	sprite.rotation = 0.0
	var b := _base_scale()
	pivot.scale = Vector2(b, b)

# ── Input ────────────────────────────────────────────────────────────────────

func _input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT:
			if event.pressed:
				idle_for = 0.0
				pressing = true
				dragging = false
				suppress_click = false
				press_pos = event.position
				grab_offset = DisplayServer.mouse_get_position() - get_window().position
				if event.double_click:
					suppress_click = true
					pet()
				elif state == State.SLEEP:
					suppress_click = true
					wake()
			else:
				if dragging:
					_end_drag()
				elif pressing and not suppress_click:
					_on_click()
				pressing = false
				dragging = false
		elif event.button_index == MOUSE_BUTTON_RIGHT and event.pressed and not dragging:
			menu.popup(Rect2i(DisplayServer.mouse_get_position(), Vector2i.ZERO))
	elif event is InputEventMouseMotion and pressing:
		if not dragging and (event.position - press_pos).length() > 6.0:
			_begin_drag()

func _on_click() -> void:
	do_hop(24.0)
	if randf() < 0.65:
		_say(QUACK_LINES[randi() % QUACK_LINES.size()])

func _begin_drag() -> void:
	dragging = true
	_kill_air()
	state = State.DRAG
	sprite.play("wave")     # flaily panic arm
	drag_samples.clear()
	# Receive mouse everywhere in the window while dragging, so fast drags
	# don't slip outside the duck-only passthrough polygon and stall.
	get_window().mouse_passthrough_polygon = PackedVector2Array()
	_say(["Hey! Put me down! ...actually this is fun.", "WHEE!", "I'm flying! (I'm being carried.)"][randi() % 3])

func _end_drag() -> void:
	sprite.play("idle")
	_update_passthrough()
	var v := Vector2.ZERO
	if drag_samples.size() >= 2:
		var a: Array = drag_samples[0]
		var c: Array = drag_samples[drag_samples.size() - 1]
		var dt_ms: float = maxf(1.0, float(c[0]) - float(a[0]))
		v = (c[1] - a[1]) / dt_ms * 1000.0
	v = v.limit_length(THROW_MAX)

	if cfg_gravity:
		state = State.FALL
		vel = v
		ang_vel = clampf(v.x * 0.004, -8.0, 8.0)
		if v.length() > 700.0:
			_say("WHEEEEEE!")
	else:
		state = State.IDLE
		idle_for = 0.0
		var b := _base_scale()
		var tw := create_tween()
		tw.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
		tw.tween_property(sprite, "rotation", 0.0, 0.3)
		tw.parallel().tween_property(pivot, "scale", Vector2(b, b), 0.3)

func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST:
		get_tree().quit()

# ── FX ───────────────────────────────────────────────────────────────────────

func _duck_top() -> float:
	return FEET_Y - DUCK_H * _base_scale() + pivot.position.y - FEET_Y

func _spawn_hearts(n: int) -> void:
	for i in range(n):
		var h := Sprite2D.new()
		h.texture = heart_tex
		h.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		h.position = Vector2(CENTER_X + randf_range(-34, 34), _duck_top() + randf_range(-6, 14))
		h.scale = Vector2.ONE * randf_range(2.0, 3.2)
		h.modulate.a = 0.0
		fx.add_child(h)
		var tw := create_tween()
		tw.set_parallel(true)
		tw.tween_property(h, "modulate:a", 1.0, 0.12)
		tw.tween_property(h, "position:y", h.position.y - randf_range(42, 74), randf_range(0.7, 1.1)).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
		tw.tween_property(h, "position:x", h.position.x + randf_range(-16, 16), 0.9)
		tw.chain().tween_property(h, "modulate:a", 0.0, 0.3)
		tw.chain().tween_callback(h.queue_free)

func _spawn_z() -> void:
	var z := Label.new()
	z.text = "Z"
	z.add_theme_font_size_override("font_size", [14, 18, 22][randi() % 3])
	z.add_theme_color_override("font_color", Color(0.65, 0.65, 1.0))
	z.position = Vector2(CENTER_X + 34.0 * _base_scale(), _duck_top() + 6)
	z.modulate.a = 0.0
	fx.add_child(z)
	var tw := create_tween()
	tw.set_parallel(true)
	tw.tween_property(z, "modulate:a", 1.0, 0.3)
	tw.tween_property(z, "position", z.position + Vector2(randf_range(8, 22), -46), 2.0).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	tw.chain().tween_property(z, "modulate:a", 0.0, 0.5)
	tw.chain().tween_callback(z.queue_free)

func _spawn_dust(n: int) -> void:
	for i in range(n):
		var d := Sprite2D.new()
		d.texture = dust_tex
		d.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		var side := -1.0 if i % 2 == 0 else 1.0
		d.position = Vector2(CENTER_X + side * randf_range(14, 30) * _base_scale(), FEET_Y - 4)
		d.scale = Vector2.ONE * randf_range(1.6, 2.8)
		fx.add_child(d)
		var tw := create_tween()
		tw.set_parallel(true)
		tw.tween_property(d, "position:x", d.position.x + side * randf_range(18, 40), 0.4).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
		tw.tween_property(d, "position:y", d.position.y - randf_range(4, 14), 0.4)
		tw.tween_property(d, "modulate:a", 0.0, 0.45)
		tw.tween_property(d, "scale", d.scale * 0.4, 0.45)
		tw.chain().tween_callback(d.queue_free)

# ── Speech bubble ────────────────────────────────────────────────────────────

func _say(text: String) -> void:
	if bubble_tween and bubble_tween.is_valid():
		bubble_tween.kill()
	bubble_label.text = text
	bubble_label.custom_minimum_size.x = minf(200.0, float(text.length()) * 7.5)
	bubble.reset_size()
	bubble.show()
	bubble_visible = true
	bubble.modulate.a = 0.0
	bubble_label.visible_ratio = 0.0
	_layout_bubble()

	bubble_tween = create_tween()
	bubble_tween.tween_property(bubble, "modulate:a", 1.0, 0.15)
	bubble_tween.parallel().tween_property(bubble_label, "visible_ratio", 1.0, minf(0.9, text.length() * 0.025))
	bubble_tween.tween_interval(2.2 + text.length() * 0.045)
	bubble_tween.tween_property(bubble, "modulate:a", 0.0, 0.3)
	bubble_tween.tween_callback(func():
		bubble.hide()
		bubble_visible = false
	)

func _layout_bubble() -> void:
	var top := FEET_Y - 138.0 * _base_scale()
	bubble.position = Vector2(
		clampf(CENTER_X - bubble.size.x * 0.5, 4.0, 320.0 - bubble.size.x - 4.0),
		maxf(4.0, top - bubble.size.y - 16.0)
	)

# ── Drawing (shadow + bubble pointer) ────────────────────────────────────────

func _draw() -> void:
	# grounding shadow
	if not (state in [State.DRAG, State.FALL]):
		var lift := FEET_Y - pivot.position.y
		var b := _base_scale()
		var w := 74.0 * b * clampf(1.0 - lift / 220.0, 0.55, 1.0)
		var alpha := 0.22 * clampf(1.0 - lift / 260.0, 0.35, 1.0)
		draw_set_transform(Vector2(CENTER_X, FEET_Y + 7.0), 0.0, Vector2(1.0, 0.26))
		draw_circle(Vector2.ZERO, w, Color(0, 0, 0, alpha))
		draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)

	# bubble pointer
	if bubble_visible and bubble.modulate.a > 0.05:
		var bx := clampf(CENTER_X, bubble.position.x + 18.0, bubble.position.x + bubble.size.x - 18.0)
		var by := bubble.position.y + bubble.size.y - 1.0
		var col := Color(1.0, 0.98, 0.88, 0.96 * bubble.modulate.a)
		draw_colored_polygon(PackedVector2Array([
			Vector2(bx - 9, by), Vector2(bx + 9, by), Vector2(bx, by + 13)
		]), col)
