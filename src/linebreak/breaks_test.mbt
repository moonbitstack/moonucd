///|
test "breaks says where a line may end and where it must" {
  assert_eq(@linebreak.breaks("ab cd\nef"), [(3, false), (6, true)])
  assert_eq(@linebreak.breaks("a\r\nb"), [(3, true)])
  assert_eq(@linebreak.breaks(""), [])
}

///|
test "an ideograph is a break opportunity on both sides" {
  assert_eq(@linebreak.linebreaks("The quick 中文 fox"), [
    "The ", "quick ", "中", "文 ", "fox",
  ])
}
