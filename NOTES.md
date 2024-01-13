## Developer Notes

```
datamodel-codegen --input docker-v1.43.yaml --input-file-type openapi --output src/dockerxxx/models.py --target-python-version 3.10 --use-schema-description --snake-case-field --collapse-root-models
```

To convert from swagger 2.0 to OpenAPI 3.0 https://stackoverflow.com/a/59749691
