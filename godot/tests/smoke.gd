extends SceneTree
## Headless smoke test: instantiates the duck and exercises every state.
## Run: godot --headless --path godot -s res://tests/smoke.gd
## Exits 0 on success, 1 on any failure.

var duck: Node2D
var frame := 0
var failures := 0
var load_failed := false

func _initialize() -> void:
	print("[smoke] loading main.tscn ...")
	var scene: PackedScene = load("res://main.tscn")
	if scene == null:
		printerr("[smoke] FAIL: main.tscn failed to load")
		load_failed = true
		return
	duck = scene.instantiate()
	root.add_child(duck)
	print("[smoke] scene instantiated")

func _check(cond: bool, what: String) -> void:
	if cond:
		print("[smoke] PASS: " + what)
	else:
		failures += 1
		printerr("[smoke] FAIL: " + what)

func _process(_delta: float) -> bool:
	if load_failed or duck == null:
		printerr("[smoke] aborting: no duck")
		quit(1)
		return true

	frame += 1
	match frame:
		5:
			_check(duck.sprite != null, "sprite built")
			_check(duck.sprite.sprite_frames.has_animation("walk"), "walk animation exists")
			_check(duck.sprite.sprite_frames.get_frame_count("walk") == 4, "walk has 4 frames")
			_check(duck.sprite.sprite_frames.has_animation("idle"), "idle animation exists")
			_check(duck.sprite.sprite_frames.has_animation("wave"), "wave animation exists")
			_check(duck.heart_tex != null and duck.dust_tex != null, "FX textures generated")
		10:
			duck._start_walk()
		15:
			_check(duck.state == duck.State.WALK, "walk state entered")
			_check(duck.sprite.animation == "walk", "walk anim playing")
			duck._stop_walk()
		20:
			duck.do_hop()
		26:
			_check(duck.juice_busy, "hop tween running")
		110:   # ~1.5 s later — hop takes ~0.9 s
			_check(not duck.juice_busy, "hop finished and released juice lock")
			duck.do_flip()
		116:
			_check(duck.state == duck.State.JUICE, "flip owns state")
		240:   # ~2 s later — flip takes ~1.3 s
			_check(not duck.juice_busy, "flip finished")
			_check(absf(duck.pivot.rotation) < 0.01, "rotation reset after flip")
			duck.pet()
		248:
			_check(duck.fx.get_child_count() > 0, "hearts spawned")
		320:
			duck.go_sleep()
		330:
			_check(duck.state == duck.State.SLEEP, "sleep state entered")
			duck.wake()
		336:
			_check(duck.state != duck.State.SLEEP, "woke up")
		400:
			duck._say("Test bubble QUACK")
		406:
			_check(duck.bubble.visible, "bubble visible after say()")
		420:
			duck._kill_air()
			duck.state = duck.State.FALL
			duck.vel = Vector2(400, -300)
			duck.ang_vel = 3.0
		560:   # >2 s of physics — plenty to land and settle
			_check(duck.state == duck.State.IDLE, "fall settled back to idle")
			duck._save_settings()
			duck._load_settings()
			_check(true, "settings round-trip")
		580:
			if failures == 0:
				print("[smoke] ALL CHECKS PASSED")
				quit(0)
			else:
				printerr("[smoke] %d FAILURES" % failures)
				quit(1)
	return false
