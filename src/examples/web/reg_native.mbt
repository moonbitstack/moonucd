///|
/// No-op registration for the native backend. The character inspector is a
/// browser demo and only does real work on the JS backend; on every other
/// backend the functions stay linked but are never wired to a global.
fn reg_char_fn(_name : String, _f : (Char) -> String) -> Unit {
  ()
}

///|
/// No-op registration for the native backend. See `reg_js.mbt`.
fn reg_str_fn(_name : String, _f : (String) -> String) -> Unit {
  ()
}
