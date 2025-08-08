from AutoFlasher.jlink_commands import CommentCommand, LoadFileCommand

def test_comment_command_uses_double_slash():
    c = CommentCommand("Hello")
    assert c.render().startswith("// "), "J-Link wants '//' comments"

def test_loadfile_renders_with_address():
    lf = LoadFileCommand("C:/firm.axf")
    s = lf.render()
    assert 'loadfile "C:/firm.axf" 0x0' in s
