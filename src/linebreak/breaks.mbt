///|
/// The break opportunities inside `s`, as the UTF-16 offset each line may
/// end at and whether the line must end there (after a hard line break) or
/// only may.
pub fn breaks(s : StringView) -> Array[(Int32, Bool)] {
  let cps = cps_of(s)
  let bounds = linebreak_boundaries(cps)
  let out = []
  let mut offset = 0
  for i in 0..<cps.length() {
    offset += cps[i].unsafe_to_char().utf16_len()
    if i < bounds.length() && bounds[i] {
      let cls = lb_lookup(cps[i])
      let mandatory = cls == lb_bk ||
        cls == lb_cr ||
        cls == lb_lf ||
        cls == lb_nl
      out.push((offset, mandatory))
    }
  }
  out
}
