from unittest import TestCase, main

from grave_settings.semantics import Semantics, Semantic, SemanticContext, Negate


class DummySemantic(Semantic[bool]):
    pass


class DummyIntSemantic(Semantic[int]):
    pass


class StackingSemantic(Semantic[int]):
    COLLECTION = set


class AbstractTestSemantics(TestCase):
    def get_semantic(self, alternate=False):
        raise NotImplementedError()

    def semantic_type(self):
        raise NotImplementedError()

    def get_semantics(self) -> Semantics:
        raise NotImplementedError()

    def test_semantics_in(self):
        s = self.get_semantics()

        self.assertNotIn(self.semantic_type(), s)
        s.add_semantics(self.get_semantic())
        self.assertIn(self.semantic_type(), s)

    def test_get_semantic_returns_None_when_not_member(self):
        s = self.get_semantics()
        self.assertIs(s[DummyIntSemantic], None)
        self.assertIs(s.get_semantic(DummySemantic), None)

    def test_del_semantic(self):
        s = self.get_semantics()
        s.add_semantics(self.get_semantic())
        self.assertIn(self.semantic_type(), s)
        del s[self.semantic_type()]
        self.assertNotIn(self.semantic_type(), s)

    def test_remove_semantic_with_value(self):
        s = self.get_semantics()
        s.add_semantics(self.get_semantic())
        self.assertIn(self.semantic_type(), s)
        s.remove_semantic(self.get_semantic())
        self.assertNotIn(self.semantic_type(), s)

        s.add_semantics(self.get_semantic())
        self.assertIn(self.semantic_type(), s)
        s.remove_semantic(self.get_semantic(alternate=True))
        self.assertIn(self.semantic_type(), s)

    def test_no_member_when_empty(self):
        s = self.get_semantics()
        self.assertNotIn(self.get_semantic(), s)
        self.assertNotIn(self.get_semantic(alternate=True), s)

    def test_update_doesnt_kill_stackers(self):
        s = self.get_semantics()
        s.add_semantics(StackingSemantic(1), StackingSemantic(2))
        s.update({StackingSemantic(0)})
        self.assertIn(StackingSemantic(0), s)
        self.assertIn(StackingSemantic(1), s)
        self.assertIn(StackingSemantic(2), s)

    def test_adding_negated_semantic_removes(self):
        s = self.get_semantics()
        s.add_semantics(self.get_semantic())
        self.assertIn(self.get_semantic(), s)
        s.add_semantics(~self.get_semantic())
        self.assertNotIn(self.get_semantic(), s)

        s = self.get_semantics()
        s.add_semantics(self.get_semantic())
        self.assertIn(self.get_semantic(), s)
        s.add_semantics(Negate(type(self.get_semantic())))
        self.assertNotIn(self.get_semantic(), s)


class TestNonStacking(AbstractTestSemantics):
    def get_semantic(self, alternate=False):
        if alternate:
            return DummySemantic(False)
        else:
            return DummySemantic(True)

    def semantic_type(self):
        return DummySemantic

    def get_semantics(self) -> Semantics:
        return Semantics()

    def test_semantic_get_full_obj(self):
        s = self.get_semantics()
        s.add_semantics(self.get_semantic())
        self.assertIsInstance(s[self.semantic_type()], self.semantic_type())

    def test_value_overwrites(self):
        s = self.get_semantics()
        s.add_semantics(self.get_semantic())
        s.add_semantics(self.get_semantic(alternate=True))
        self.assertFalse(s[self.semantic_type()])

    def test_pop_semantic_type(self):
        s = self.get_semantics()
        s.add_semantics(self.get_semantic())
        self.assertIn(self.semantic_type(), s)
        sem = s.pop(self.semantic_type())
        self.assertNotIn(self.semantic_type(), s)
        self.assertIsInstance(sem, self.semantic_type())
        self.assertEqual(sem.val, True)

    def test_semantic_retains_value(self):
        s = self.get_semantics()
        s.add_semantics(self.get_semantic())
        self.assertTrue(s[self.semantic_type()])

        s = self.get_semantics()
        s.add_semantics(self.get_semantic(alternate=True))
        self.assertFalse(s[self.semantic_type()])

    def test_parent_overrides(self):
        s = self.get_semantics()
        parent = self.get_semantics()
        s.parent = parent
        s.add_semantics(self.get_semantic())
        self.assertTrue(s[self.semantic_type()])
        parent.add_semantics(self.get_semantic(alternate=True))
        self.assertFalse(s[self.semantic_type()])
        self.assertNotIn(self.get_semantic(), s)

    def test_get_semantic_does_not_get_from_parent(self):
        s = self.get_semantics()
        parent = self.get_semantics()
        s.parent = parent
        s.add_semantics(self.get_semantic())
        self.assertTrue(s.get_semantic(self.semantic_type()))
        parent.add_semantics(self.get_semantic(alternate=True))
        self.assertTrue(s.get_semantic(self.semantic_type()))
        self.assertNotIn(self.get_semantic(), s)

    def test_update_semantics_with_set(self):
        s = self.get_semantics()
        s.add_semantics(self.get_semantic(alternate=False))
        sems = self.get_semantics()
        sems.update({self.get_semantic(alternate=True)})
        s.update(sems)
        self.assertIn(self.get_semantic(alternate=True), s)
        self.assertNotIn(self.get_semantic(alternate=False), s)


class TestStackerSemantics(AbstractTestSemantics):
    def get_semantic(self, alternate=False):
        if alternate:
            return StackingSemantic(0)
        else:
            return StackingSemantic(2)

    def semantic_type(self):
        return StackingSemantic

    def get_semantics(self) -> Semantics:
        return Semantics()

    def test_semantic_get_full_obj(self):
        s = self.get_semantics()
        s.add_semantics(self.get_semantic())
        self.assertIsInstance(s[self.semantic_type()], set)

    def test_value_stacks(self):
        s = self.get_semantics()
        s.add_semantics(self.get_semantic())
        s.add_semantics(self.get_semantic(alternate=True))
        self.assertIn(self.get_semantic(), s)
        self.assertIn(self.get_semantic(alternate=True), s)

    def test_pop_semantic_type(self):
        s = self.get_semantics()
        s.add_semantics(self.get_semantic())
        self.assertIn(self.semantic_type(), s)
        sem = s.pop(self.semantic_type())
        self.assertNotIn(self.semantic_type(), s)
        self.assertIsInstance(sem, set)
        self.assertIn(self.get_semantic(), sem)

    def test_semantic_values(self):
        s = self.get_semantics()
        s.add_semantics(self.get_semantic())
        self.assertIn(self.get_semantic(), s[self.semantic_type()])

        s.add_semantics(self.get_semantic(alternate=True))
        b = s[self.semantic_type()]
        self.assertIn(self.get_semantic(), b)
        self.assertIn(self.get_semantic(alternate=True), b)

    def test_semantics_stack_with_parent(self):
        s = self.get_semantics()
        parent = self.get_semantics()
        s.parent = parent
        s.add_semantics(self.get_semantic())
        self.assertIn(self.get_semantic(), s[self.semantic_type()])
        self.assertIn(self.get_semantic(), s)

        parent.add_semantics(self.get_semantic(alternate=True))
        self.assertIn(self.get_semantic(), s)
        self.assertIn(self.get_semantic(alternate=True), s)

    def test_update_semantics_with_set(self):
        s = self.get_semantics()
        s.add_semantics(self.get_semantic(alternate=False))
        sems = {self.get_semantic(alternate=True)}
        s.update(sems)
        self.assertIn(self.get_semantic(alternate=True), s)
        self.assertIn(self.get_semantic(alternate=False), s)

    def test_update_semantics_with_semantics(self):
        s = self.get_semantics()
        s.add_semantics(self.get_semantic(alternate=False))
        sems = self.get_semantics()
        sems.update({self.get_semantic(alternate=True)})
        s.update(sems)
        self.assertIn(self.get_semantic(alternate=True), s)
        self.assertIn(self.get_semantic(alternate=False), s)


class TestSemanticContext(TestCase):
    def get_semantics(self) -> SemanticContext:
        return SemanticContext(Semantics())

    def test_stack_returns_to_None(self):
        with self.get_semantics() as s:
            s.add_semantics(DummySemantic(True))
        self.assertNotIn(DummySemantic, s)

    def test_stack_returns_to_val(self):
        s = self.get_semantics()
        s.add_semantics(DummySemantic(True))
        with s:
            s.add_semantics(DummySemantic(False))
            self.assertFalse(s[DummySemantic])
        self.assertTrue(s[DummySemantic])

    def test_walk_stack_frame(self):
        s = self.get_semantics()
        with s:
            s.add_frame_semantics(DummyIntSemantic(5))
            with s:
                s.add_frame_semantics(DummyIntSemantic(7))
                with s:
                    s.add_frame_semantics(DummyIntSemantic(20))
                    with s:
                        with s:
                            s.add_frame_semantics(DummyIntSemantic(99))
                            self.assertEqual(s[DummyIntSemantic], DummyIntSemantic(99))
                        self.assertEqual(s[DummyIntSemantic], None)
                    self.assertEqual(s[DummyIntSemantic], DummyIntSemantic(20))
                self.assertEqual(s[DummyIntSemantic], DummyIntSemantic(7))
            self.assertEqual(s[DummyIntSemantic], DummyIntSemantic(5))
        self.assertEqual(s[DummyIntSemantic], None)

    def test_walk_stack_pool(self):
        s = self.get_semantics()
        with s:
            s.add_semantics(DummyIntSemantic(5))
            with s:
                s.add_semantics(DummyIntSemantic(7))
                with s:
                    s.add_semantics(DummyIntSemantic(20))
                    with s:
                        with s:
                            s.add_semantics(DummyIntSemantic(99))
                            self.assertEqual(s[DummyIntSemantic], DummyIntSemantic(99))
                        self.assertEqual(s[DummyIntSemantic], DummyIntSemantic(20))  # copies over
                    self.assertEqual(s[DummyIntSemantic], DummyIntSemantic(20))
                self.assertEqual(s[DummyIntSemantic], DummyIntSemantic(7))
            self.assertEqual(s[DummyIntSemantic], DummyIntSemantic(5))
        self.assertEqual(s[DummyIntSemantic], None)

    def test_transfers_semantics_up_not_down(self):
        class FooSemantic(Semantic[str]):
            pass

        s = self.get_semantics()
        with s:
            s.add_semantics(DummyIntSemantic(5))
            s.add_semantics(DummySemantic(True))
            with s:
                s.add_semantics(FooSemantic('test'))
                self.assertIn(DummySemantic, s)
                self.assertIn(DummyIntSemantic, s)
                self.assertEqual(s[DummyIntSemantic].val, 5)
                self.assertEqual(s[DummySemantic].val, True)
                s.add_semantics(DummySemantic(False))
                with s:
                    s.add_semantics(DummyIntSemantic(2))
                    self.assertIn(DummySemantic, s)
                    self.assertIn(FooSemantic, s)
                    self.assertIn(DummyIntSemantic, s)
                    self.assertEqual(s[DummyIntSemantic].val, 2)
                    self.assertEqual(s[FooSemantic].val, 'test')
                    self.assertEqual(s[DummySemantic].val, False)
                    self.assertNotIn(DummySemantic(True), s)
                self.assertIn(DummySemantic, s)
                self.assertIn(DummyIntSemantic, s)
                self.assertEqual(s[DummyIntSemantic].val, 5)
                self.assertEqual(s[DummySemantic].val, False)
                self.assertEqual(s[FooSemantic].val, 'test')
                self.assertNotIn(DummySemantic(True), s)
            self.assertIn(DummySemantic, s)
            self.assertIn(DummyIntSemantic, s)
            self.assertEqual(s[DummyIntSemantic].val, 5)
            self.assertEqual(s[DummySemantic].val, True)
            self.assertEqual(s[FooSemantic], None)
            self.assertNotIn(FooSemantic, s)
            self.assertNotIn(DummySemantic(False), s)
        self.assertNotIn(DummySemantic, s)
        self.assertNotIn(DummyIntSemantic, s)
        self.assertEqual(s[DummyIntSemantic], None)
        self.assertEqual(s[DummySemantic], None)
        self.assertNotIn(DummySemantic(True), s)

    def test_transfers_stacking_semantics_up_not_down(self):
        s = self.get_semantics()
        with s:
            s.add_semantics(StackingSemantic(1))
            with s:
                s.add_semantics(StackingSemantic(2))
                self.assertIn(StackingSemantic(1), s[StackingSemantic])
                self.assertIn(StackingSemantic(2), s[StackingSemantic])
            self.assertIn(StackingSemantic(1), s[StackingSemantic])
            self.assertNotIn(StackingSemantic(2), s[StackingSemantic])
        self.assertNotIn(StackingSemantic, s)

    def test_transfers_parent_up_not_down(self):
        s = self.get_semantics()
        with s:
            s.add_frame_semantics(StackingSemantic(1))
            with s:
                s.add_frame_semantics(StackingSemantic(2))
                self.assertNotIn(StackingSemantic(1), s[StackingSemantic])
                self.assertIn(StackingSemantic(2), s[StackingSemantic])
            self.assertIn(StackingSemantic(1), s[StackingSemantic])
            self.assertNotIn(StackingSemantic(2), s[StackingSemantic])
        self.assertNotIn(StackingSemantic, s)

        s = self.get_semantics()
        with s:
            s.parent = 'test'
            with s:
                s.parent = 'tt'
                with s:
                    s.parent = 'foo'
                self.assertEqual(s.parent, 'tt')
            self.assertEqual(s.parent, 'test')
        self.assertEqual(s.parent, None)

    def test_semantic_frame_override(self):
        s = self.get_semantics()
        s.add_semantics(DummyIntSemantic(5))
        s.add_frame_semantics(DummyIntSemantic(6))
        self.assertEqual(s[DummyIntSemantic].val, 6)
        s.remove_frame_semantic(DummyIntSemantic)
        self.assertEqual(s[DummyIntSemantic].val, 5)

    def test_semantic_frame_merge_collection(self):
        s = self.get_semantics()
        s.add_semantics(StackingSemantic(0))
        s.add_frame_semantics(StackingSemantic(1))
        colec = s[StackingSemantic]
        self.assertIn(StackingSemantic(0), colec)
        self.assertIn(StackingSemantic(1), colec)
        with s:
            s.add_frame_semantics(StackingSemantic(3))
            colec = s[StackingSemantic]
            self.assertIn(StackingSemantic(0), colec)
            self.assertIn(StackingSemantic(3), colec)
        colec = s[StackingSemantic]
        self.assertIn(StackingSemantic(0), colec)
        self.assertIn(StackingSemantic(1), colec)


class ContextTestNonStacking(TestNonStacking):
    def get_semantics(self) -> Semantics:
        return SemanticContext(Semantics())


class ContextTestStackerSemantics(TestStackerSemantics):
    def get_semantics(self) -> Semantics:
        return SemanticContext(Semantics())


del AbstractTestSemantics
if __name__ == '__main__':
    main()
