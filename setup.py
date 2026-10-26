from pathlib import Path
import shutil

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py


class build_py(_build_py):
    def run(self):
        super().run()
        source = Path(__file__).parent / "skills"
        target = Path(self.build_lib) / "gpe" / "_skills"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)


setup(cmdclass={"build_py": build_py})
