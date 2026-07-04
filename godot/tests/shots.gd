extends SceneTree
## Captures real rendered screenshots of the duck in several states.
## Run under xvfb with GL: godot --path godot -s res://tests/shots.gd
## Writes PNGs (with alpha) into $SHOTS_DIR.

var duck: Node2D
var frame := 0
var dir := ""

func _initialize() -> void:
	dir = OS.get_environment("SHOTS_DIR")
	if dir == "":
		dir = "/tmp/shots"
	DirAccess.make_dir_recursive_absolute(dir)
	var scene: PackedScene = load("res://main.tscn")
	duck = scene.instantiate()
	root.add_child(duck)
	print("[shots] capturing to " + dir)

func _cap(name: String) -> void:
	var img: Image = root.get_texture().get_image()
	img.save_png(dir + "/" + name + ".png")
	print("[shots] saved " + name + ".png")

func _process(_delta: float) -> bool:
	frame += 1
	match frame:
		8:
			duck._say("QUACK! I'm rendered by Godot now!")
		30:
			_cap("idle_bubble")
		35:
			duck.pet()
		50:
			_cap("hearts")
		95:
			duck._start_walk()
			duck.sprite.flip_h = false
		112:
			_cap("walk")
			duck._stop_walk()
		122:
			duck.do_flip()
		140:
			_cap("flip_mid")
		200:
			duck.do_stretch()
		228:
			_cap("stretch")
		270:
			duck.do_shake()
			duck.emote("!")
		276:
			_cap("shake")
		320:
			duck.do_peck()
		330:
			_cap("peck")
		380:
			duck.go_sleep()
		435:
			_cap("sleep")
		450:
			print("[shots] DONE")
			quit(0)
	return false
