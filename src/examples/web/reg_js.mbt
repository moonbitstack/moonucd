///|
/// Expose a `(Char) -> String` MoonBit function on the JavaScript global object.
/// Compiled only for the JS backend (see the `*_native` / `*_wasm` siblings and
/// the `targets` map in `moon.pkg`). `name` is read during the call (borrow);
/// `f` is stored on the global object afterwards (owned).
#borrow(name)
extern "js" fn reg_char_fn(name : String, f : (Char) -> String) -> Unit =
  #| function(name, f) { globalThis[name] = f; }

///|
/// Expose a `(String) -> String` MoonBit function on the JavaScript global object.
/// Compiled only for the JS backend (see the `*_native` / `*_wasm` siblings and
/// the `targets` map in `moon.pkg`). `name` is read during the call (borrow);
/// `f` is stored on the global object afterwards (owned).
#borrow(name)
extern "js" fn reg_str_fn(name : String, f : (String) -> String) -> Unit =
  #| function(name, f) { globalThis[name] = f; }
