import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

// 运行时配置与后端共用 apps/.env，不在代码里保留回退值。
const ENV_FILE = fileURLToPath(new URL("../.env", import.meta.url));

function parseEnvFile(file: string): Record<string, string> {
  let text: string;
  try {
    text = readFileSync(file, "utf8");
  } catch {
    throw new Error(`无法读取 ${file}，请从 apps/.env.example 复制后填写`);
  }

  const values: Record<string, string> = {};
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;

    const separator = line.indexOf("=");
    if (separator === -1) continue;

    const key = line.slice(0, separator).trim();
    let value = line.slice(separator + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    values[key] = value;
  }
  return values;
}

const fileEnv = parseEnvFile(ENV_FILE);

export function requireEnv(key: string): string {
  const value = fileEnv[key];
  if (value === undefined || value === "") {
    throw new Error(`缺少环境变量 ${key}，请在 ${ENV_FILE} 中配置`);
  }
  return value;
}
