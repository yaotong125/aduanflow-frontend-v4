import { mockCases } from '../../frontend/src/data/mockData.js';
import fs from 'fs';

fs.writeFileSync('../mock_cases.json', JSON.stringify(mockCases, null, 2));
console.log('Mock cases written to mock_cases.json');
