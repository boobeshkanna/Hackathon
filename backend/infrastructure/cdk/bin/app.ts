#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { VernacularArtisanCatalogStack } from '../lib/stack';

const app = new cdk.App();

new VernacularArtisanCatalogStack(app, 'VernacularArtisanCatalogStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'ap-south-1',
  },
  description: 'Vernacular Artisan Catalog - ONDC Integration Infrastructure',
});

app.synth();
