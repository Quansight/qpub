from .__init__ import *


def test_nox():
    return Task()


def test_tox():
    return Task()


def task_test():
    def test(monkeytype, extra):
        import doit

        extra = extra or []

        if monkeytype:
            needs("pytest", "monkeytype")
            assert not doit.tools.LongRunning(
                f"""monkeytype pytest {" ".join(extra)}"""
            ).execute()
        else:
            needs("pytest")
            assert not doit.tools.LongRunning(f"""pytest {" ".join(extra)}""").execute()

    return Task(actions=[test], params=[Param("monkeytype", False)], pos_arg="extra")


if __name__ == "__main__":

    def tox_conf():
        return False

    def nox_conf():
        return NOXFILE.exists()

    DOIT_CONFIG["default_tasks"] += [
        "nox" if nox_conf() else "tox" if tox_conf() else "test"
    ]

    main(globals())