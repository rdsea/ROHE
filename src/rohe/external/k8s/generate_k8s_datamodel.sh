#! /bin/bash

# Download the openapi schema at https://github.com/kubernetes/kubernetes/tree/master/api/openapi-spec
# apis__apps__v1_openapi.json
# api__v1_openapi.json
#
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
DATAMODEL_DIR="${SCRIPT_DIR}/datamodel"

if [ -d "$DATAMODEL_DIR" ]; then
	rm -rf "$DATAMODEL_DIR"
	echo "Deleted the datamodel folder."
else
	echo "The datamodel folder does not exist."
fi

mkdir "$DATAMODEL_DIR"
echo "Recreated the datamodel folder."
#WARNING: dont' delete this --collapse-root-models flag, it'll just work
datamodel-codegen --snake-case-field --input "$SCRIPT_DIR/apis__apps__v1_openapi.json" --output "$DATAMODEL_DIR" \
	--output-model-type=pydantic_v2.BaseModel \
	--target-python-version=3.10 \
	--collapse-root-models \
	--use-default-kwarg \
	--use-union-operator \
	--use-standard-collections

datamodel-codegen --snake-case-field --input "$SCRIPT_DIR/api__v1_openapi.json" --output "$DATAMODEL_DIR" \
	--output-model-type=pydantic_v2.BaseModel \
	--target-python-version=3.10 \
	--collapse-root-models \
	--use-default-kwarg \
	--use-union-operator \
	--use-standard-collections

mv "$DATAMODEL_DIR/io/k8s/api" "$DATAMODEL_DIR"
mv "$DATAMODEL_DIR/io/k8s/apimachinery" "$DATAMODEL_DIR"
rm -r "$DATAMODEL_DIR/io"
