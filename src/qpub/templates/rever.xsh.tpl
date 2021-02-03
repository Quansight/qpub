
# the project name inferred from qpub
$PROJECT = '{{name}}'

# a list of activities to add.
# some references
# https://github.com/Quansight/intake-omnisci/blob/master/rever.xsh
# https://github.com/Quansight/ibis-vega-transform/blob/master/rever.xsh
$ACTIVITIES = [
              'version_bump',  # Changes the version number in various source files (setup.py, __init__.py, etc)
              'changelog',  # Uses files in the news folder to create a changelog for release
              # 'pypi',  # use github actions to send the package to pypi 
              # 'conda_forge',  # this will be handy reates a PR into your package's feedstock
               ]
if $CI:
    $ACTIVITIES += [
        'ghrelease'  # Creates a Github release entry for the new tag
        'tag',  # Creates a tag for the new version number
        'push_tag',  # Pushes the tag up to the $TAG_REMOTE
    ]

$VERSION_BUMP_PATTERNS = [  # These note where/how to find the version numbers
                         ('{{init_file}}', r"__version__\s*=.*", "__version__ = '$VERSION'"),
                         ('setup.py', r"version\s*=.*,", "version='$VERSION',")
                         ]

# there is logic to bump the patterns                         
$CHANGELOG_FILENAME = 'CHANGELOG.rst'  # Filename for the changelog
$CHANGELOG_TEMPLATE = 'TEMPLATE.rst'  # Filename for the news template

if "ssh" and None:
    $PUSH_TAG_REMOTE = '{{repo}}'  # Repo to push tags to

$GITHUB_ORG = '{{org}}'  # Github org for Github releases and conda-forge
$GITHUB_REPO = '{{name}}'  # Github repo for Github releases and conda-forge