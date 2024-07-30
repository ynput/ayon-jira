import { Panel } from "@ynput/ayon-react-components";
import styled from "styled-components";

export const Container = styled(Panel)`
  max-width: 800px;
  margin: 32px auto;
  display: flex;
  flex-direction: column;
  gap: 16px;

  button.save {
    margin-left: auto;
    padding: 4px 8px;
  }

  h2 {
    font-size: 22px;
  }
`;

export const Form = styled.div`
  display: grid;
  grid-template-columns: auto 1fr;
  align-items: center;
  grid-gap: 8px 32px;
`;

const Message = styled.span`
  padding: 8px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
`;

export const Error = styled(Message)`
  background-color: var(--md-sys-color-error-container);
  &,
  .icon {
    color: var(--md-sys-color-on-error-container);
  }
`;

export const Success = styled(Message)`
  background-color: var(--md-sys-color-primary);

  &,
  .icon {
    color: var(--md-sys-color-on-primary);
  }
`;
